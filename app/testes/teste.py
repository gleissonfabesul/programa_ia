import os
import pickle
import asyncio
from typing import List, Optional, TypedDict
import numpy as np
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.repositories.repositorio_produtos import RepositorioProdutos
from langgraph.graph import StateGraph, END

# Nome do arquivo onde salvaremos o cache dos vetores do catálogo
ARQUIVO_VETORES_CACHE = "app/catalogo_vetores_cache.pkl"

# --- Modelos para Resposta Estruturada da OpenAI ---
class MatchResult(BaseModel):
    original_query: str = Field(description="O nome exato do produto que foi enviado para busca")
    matched_id: Optional[str] = Field(description="O 'cpro' do produto no banco")
    matched_name: Optional[str] = Field(description="O 'descr' oficial no banco")
    found: bool

class MatchBatch(BaseModel):
    matches: List[MatchResult]

class PendingItem(TypedDict):
    name: str
    quantity: str

class ExtractedItem(BaseModel):
    product_name: str = Field(description="Nome completo do produto solicitado")
    quantidade: str = Field(description="Apenas o número da quantidade (ex: 8.00, 2.00, 15.00)")

class ExtractionBatch(BaseModel):
    items: List[ExtractedItem]

# --- Estado do Grafo ---
class AgentState(TypedDict):
    customer_id: int
    raw_request: str
    pending_items: List[PendingItem]
    history_pool: List[dict]
    contract_pool: List[dict]
    final_results: List[dict]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
extraction_llm = llm.with_structured_output(ExtractionBatch)
mapper_llm = llm.with_structured_output(MatchBatch)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
repo = RepositorioProdutos() # Instanciado fora ou dentro da função

async def carregar_ou_criar_cache_vetorial(forcar_atualizacao: bool = False) -> List[dict]:
    """
    Gerencia o cache local dos vetores. Se o arquivo não existir ou forçar_atualizacao for True,
    ele busca todo o catálogo no banco, gera os vetores na OpenAI e salva no disco.
    """
    if os.path.exists(ARQUIVO_VETORES_CACHE) and not forcar_atualizacao:
        print(f"[VETORES] 💾 Carregando {ARQUIVO_VETORES_CACHE} da memória local...")
        with open(ARQUIVO_VETORES_CACHE, "rb") as f:
            return pickle.load(f)
            
    print("[VETORES] 🔄 Gerando nova base de dados vetorial. Isso pode levar alguns segundos...")
    
    catalog_completo = await repo.buscar_catalogo_produtos()
    
    descricoes = [prod["descr"] for prod in catalog_completo]
    print(f"[VETORES] 🧠 Enviando {len(descricoes)} descrições para a OpenAI gerar os Embeddings...")
    
    vetores_gerados = await embeddings_model.aembed_documents(descricoes)
    
    catalogo_vetorial = []
    for produto, vetor in zip(catalog_completo, vetores_gerados):
        catalogo_vetorial.append({
            "cpro": produto["cpro"],
            "descr": produto["descr"],
            "disp": produto.get("disp", 0),
            "preco": produto.get("precal") or produto.get("prec") or produto.get("preco") or 0.0,
            "vetor": vetor
        })
        
    with open(ARQUIVO_VETORES_CACHE, "wb") as f:
        pickle.dump(catalogo_vetorial, f)
        
    print(f"[VETORES] ✅ Cache vetorial salvo com sucesso em: {ARQUIVO_VETORES_CACHE}")
    return catalogo_vetorial

async def extraction_node(state: AgentState):
    """Passo 1: Extrai produtos e quantidades com foco em separar especificações de quantidades."""
    
    prompt = f"""
    Analise o pedido e extraia os itens. 
    DICA: No texto, a especificação (ex: 500ml) é diferente da quantidade pedida (ex: 2,00 Pç).
    
    Exemplo: "Borrifador... 500ml 2,00 Pç" 
    -> Produto: "Borrifador de Plastico Com Gatilho 500ml"
    -> Quantidade: "2.00"
    
    PEDIDO: {state['raw_request']}
    """

    print("Extraindo dados do pedido...")

    res = await extraction_llm.ainvoke(prompt)
    
    # AJUSTADO: Mapeamento corrigido para ler do modelo ExtractionBatch (.items e .product_name)
    pending = [{"name": m.product_name, "quantity": m.quantidade} for m in res.items]
    
    history = await repo.buscar_historico_produtos(state["customer_id"])
    contract = await repo.buscar_produtos_contrato(state["customer_id"])
    
    return {
        "pending_items": pending,
        "history_pool": history,
        "contract_pool": contract,
        "final_results": []
    }

async def match_history_node(state: AgentState):
    """Passo 2: Busca no Histórico carregando a quantidade com controle estável via Python."""
    if not state["pending_items"]: return state

    print("Buscando itens dos pedidos anteriores...")
    
    nomes_pendentes = [i["name"] for i in state["pending_items"]]
    prompt = f"""
    Mapeie os itens solicitados pelo cliente no HISTÓRICO de compras dele.
    
    DIRETRIZES DE EQUIVALÊNCIA COMERCIAL:
    1. "Água Sanitária" e "Alvejante" são sinônimos exatos. Se o cliente pediu "Água Sanitária" e no histórico constar "Alvejante" (ou vice-versa) de mesma volumetria, considere MATCH (found: True).
    2. IGNORE marcas, siglas ou especificações químicas adicionais trazidas no pedido do cliente que possam gerar falsos negativos (ex: ignore marcas como "- APS", "APS", e textos como "Cloro Ativo 2 a 2.5%"). Foque no tipo de produto e tamanho.
    3. Trava de Volumetria: Um produto de 5 Litros NUNCA pode casar com um de 1 Litro ou ml.
    
    ITENS SOLICITADOS (Cliente): {nomes_pendentes}
    HISTÓRICO DISPONÍVEL (Banco): {state['history_pool']}
    """
    response = await mapper_llm.ainvoke(prompt)
    
    # Cria um mapa de respostas da IA indexado por nome original limpo
    matches_ia = {m.original_query.lower().strip(): m for m in response.matches}
    
    found = []
    still_pending = []
    
    # O Python gerencia o loop baseado no que entrou, impedindo sumiço de itens
    for item in state["pending_items"]:
        match_llm = matches_ia.get(item["name"].lower().strip())
        
        if match_llm and match_llm.found:
            item_db = next((x for x in state["history_pool"] if str(x.get('cpro')) == str(match_llm.matched_id)), {})
            found.append({
                "id": match_llm.matched_id, 
                "name": match_llm.matched_name, 
                "quantidade": item["quantity"], 
                "preco": item_db.get("prec") or item_db.get("preco") or item_db.get("precal") or 0.0,
                "source": "history",
                "disp": item_db.get('disp', 0)
            })
        else:
            still_pending.append(item)
            
    return {"pending_items": still_pending, "final_results": state["final_results"] + found}

async def match_contract_node(state: AgentState):
    """Passo 3: Busca inteligente no Contrato com controle estável via Python."""
    if not state["pending_items"]: return state

    print("Buscando dados do contrato...")
    
    nomes_pendentes = [i["name"] for i in state["pending_items"]]
    prompt = f"""
    Mapeie os itens restantes no CONTRATO de fornecimento do cliente. 
    
    DIRETRIZES DE EQUIVALÊNCIA COMERCIAL:
    1. "Água Sanitária" e "Alvejante" são sinônimos exatos. Se o cliente pediu "Água Sanitária" e no contrato constar "Alvejante" (ou vice-versa) de mesma volumetria, considere MATCH (found: True).
    2. IGNORE marcas, siglas ou especificações químicas adicionais trazidas no pedido do cliente que possam gerar falsos negativos (ex: ignore marcas como "- APS", "APS", e textos como "Cloro Ativo 2 a 2.5%"). Foque no tipo de produto e tamanho.
    3. Trava de Volumetria: Um produto de 5 Litros NUNCA pode casar com um de 1 Litro ou ml.
    
    RESTANTES SOLICITADOS (Cliente): {nomes_pendentes}
    CONTRATO DISPONÍVEL (Banco): {state['contract_pool']}
    """
    response = await mapper_llm.ainvoke(prompt)
    
    matches_ia = {m.original_query.lower().strip(): m for m in response.matches}
    
    found = []
    still_pending = []
    
    for item in state["pending_items"]:
        match_llm = matches_ia.get(item["name"].lower().strip())
        
        if match_llm and match_llm.found:
            item_db = next((x for x in state["contract_pool"] if str(x.get('cpro')) == str(match_llm.matched_id)), {})
            found.append({
                "id": match_llm.matched_id, 
                "name": match_llm.matched_name, 
                "quantidade": item["quantity"], 
                "preco": item_db.get("prec") or item_db.get("preco") or item_db.get("precal") or item_db.get("prect") or 0.0 ,
                "source": "contract",
                "disp": item_db.get('disp', 0)
            })
        else:
            still_pending.append(item)
            
    return {"pending_items": still_pending, "final_results": state["final_results"] + found}

async def match_catalog_node(state: AgentState):
    """Passo 4: Busca Semântica/Vetorial Inteligente (Resolve 'Água Sanitária' vs 'Alvejante')"""
    if not state["pending_items"]: return state
    print("[AGENTE] Acionando Mecanismo Vetorial do Catálogo Geral...")
    
    catalogo_vetorial = await carregar_ou_criar_cache_vetorial()

    print("Buscando dados dos produtos gerais...")
    
    found_in_catalog = []
    for item in state["pending_items"]:
        vetor_pedido = await embeddings_model.aembed_query(item["name"])
        
        vetores_banco = np.array([prod["vetor"] for prod in catalogo_vetorial])
        similaridades = np.dot(vetores_banco, vetor_pedido)
        
        indices_top = np.argsort(similaridades)[-15:][::-1]
        
        pool_reduzido = []
        for idx in indices_top:
            prod_vetor = catalogo_vetorial[idx]
            pool_reduzido.append({
                "cpro": prod_vetor["cpro"],
                "descr": prod_vetor["descr"],
                "disp": prod_vetor["disp"],
                "preco": prod_vetor.get("preco", 0.0)
            })

        prompt = f"""
        Encontre o melhor match para o produto solicitado: '{item['name']}'
        OPÇÕES DISPONÍVEIS NO BANCO (Selecionadas por proximidade conceitual): {pool_reduzido}
        
        REGRAS CRÍTICAS:
        1. Se nenhum produto for similar de verdade ou tiver volumetria menor, retorne found: False.
        2. Bloqueio de tamanho: Se o cliente pediu 5 Litros, você não pode mapear para embalagens de ml.
        """
        response = await mapper_llm.ainvoke(prompt)
        
        if response.matches and response.matches[0].found:
            m = response.matches[0]
            item_db = next(x for x in pool_reduzido if str(x['cpro']) == str(m.matched_id))
            found_in_catalog.append({
                "id": m.matched_id, "name": m.matched_name,
                "quantidade": item["quantity"], "source": "catalog",
                "disp": item_db.get('disp', 0),
                "preco": item_db.get("preco", 0.0),
            })
        else:
            found_in_catalog.append({
                "id": "N/A", "name": f"{item['name']} (Não encontrado)",
                "quantidade": item["quantity"], "source": "catalog", "disp": 0, "preco": 0.0,
            })
            
    return {"pending_items": [], "final_results": state["final_results"] + found_in_catalog}

async def inventory_node(state: AgentState):
    """Verifica o estoque e sugere similares se necessário."""
    validated_results = []

    print("Validadndo estoque de produtos")
    
    for item in state["final_results"]:
        if item["id"] == "N/A":
            validated_results.append(item)
            continue
            
        try:
            qtd_solicitada = float(item["quantidade"])
        except:
            qtd_solicitada = 0.0

        estoque_atual = float(item.get("disp", 0))

        if estoque_atual >= qtd_solicitada:
            print("VALOR ESTOQUE ATUAL", estoque_atual, "VALOR ESTOQUE SOLICITADO", qtd_solicitada)
            item["status_estoque"] = "OK"
            validated_results.append(item)
        else:
            print(f"⚠️ Sem estoque para {item['name']}. Buscando similar...")
            similares = await repo.buscar_similares_com_estoque(item["name"])
            
            if similares:
                prompt = f"""
                O produto '{item['name']}' está sem estoque. 
                Escolha o substituto mais adequado da lista abaixo:
                {similares}
                """
                escolha = await llm.ainvoke(prompt)
                
                substituto = similares[0]
                validated_results.append({
                    "id": substituto["cpro"],
                    "name": substituto["descr"],
                    "quantidade": item["quantidade"],
                    "source": f"substituição (original: {item['id']})",
                    "preco": substituto.get("precal") or substituto.get("prec") or substituto.get("preco") or 0.0,
                    "status_estoque": "SUBSTITUÍDO"
                })
            else:
                item["status_estoque"] = "SEM ESTOQUE / SEM SIMILAR"
                validated_results.append(item)

    return {"final_results": validated_results}

workflow = StateGraph(AgentState)

workflow.add_node("extraction", extraction_node)
workflow.add_node("match_history", match_history_node)
workflow.add_node("match_contract", match_contract_node)
workflow.add_node("match_catalog", match_catalog_node)
workflow.add_node("inventory_check", inventory_node)

workflow.set_entry_point("extraction")
workflow.add_edge("extraction", "match_history")
workflow.add_edge("match_history", "match_contract")
workflow.add_edge("match_contract", "match_catalog")
workflow.add_edge("match_catalog", "inventory_check")
workflow.add_edge("inventory_check", END)

app = workflow.compile()

async def rodar_agente():
    input_data = {
        "customer_id": 4784,
        "raw_request": """Agua Sanitaria Cloro Ativo 2 a 2.5% 5 Litros - APS 8,00 Gl 8,8500 70,80,
          Borrifador de Plastico Com Gatilho 500ml 2,00 Pç 6,9800 13,96,
            Copo Plástico Descartavel 200ml Pacote C/10015,00 pct 4,
            3000 64,50 Desinfetante Liquido C/ Aroma de Pinho ou Eucalipto 500ml - APS 10,00 Fr 2,2800 22,80, pandorga 10 un, Cola Super Bonder 3G Henkel 5 un, Chá Matte Leão Cx C/25 Un 1,6g Natural Ref. 1201 10 un"""
    }

    output = await app.ainvoke(input_data)

    print(f"\n{'CPRO':<10} | {'DESCRIÇÃO NO BANCO':<40} | {'QTD':<12} | {'PREÇO':<12} | {'FONTE':<15}")
    print("-" * 100)
    
    for res in output["final_results"]:
        cpro = str(res.get('id', 'N/A'))
        nome = (res.get('name') or "N/A")[:35]
        qtd  = str(res.get('quantidade', 'N/A'))
        preco = f"R$ {float(res.get('preco', 0.0)):.2f}"
        src  = str(res.get('source', 'N/A')).upper()
        
        print(f"{cpro:<10} | {nome:<40} | {qtd:<12} | {preco:<12} | {src:<15}")

if __name__ == "__main__":
    asyncio.run(rodar_agente())