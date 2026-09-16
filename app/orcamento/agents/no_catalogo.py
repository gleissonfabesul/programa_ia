import os
import json
import pickle
import asyncio
import numpy as np
from app.utils.logger import logger
from datetime import datetime
from typing import List
from app.orcamento.estado_orcamento import AgentState
from app.configs.confgLang import mapper_llm, embeddings_model, repo, ARQUIVO_VETORES_CACHE, ARQUIVO_CONTROLE_CACHE

async def carregar_ou_criar_cache_vetorial(forcar_atualizacao: bool = False) -> List[dict]:

    hoje = datetime.now().strftime("%Y-%m-%d")

    # ==========================================
    # VALIDA SE O CACHE JÁ FOI GERADO HOJE
    # ==========================================
    cache_valido_hoje = False

    if os.path.exists(ARQUIVO_CONTROLE_CACHE):
        with open(ARQUIVO_CONTROLE_CACHE, "r") as f:
            data_cache = f.read().strip()

        if data_cache == hoje:
            cache_valido_hoje = True

    # ==========================================
    # USA CACHE EXISTENTE
    # ==========================================
    if (
        os.path.exists(ARQUIVO_VETORES_CACHE)
        and cache_valido_hoje
        and not forcar_atualizacao
    ):
        # logger.info("[VETORES] ✅ Cache vetorial carregado do disco.")

        with open(ARQUIVO_VETORES_CACHE, "rb") as f:
            return pickle.load(f)

    # ==========================================
    # REGERA CACHE
    # ==========================================
    logger.info("[VETORES] 🔄 Gerando nova base vetorial do catálogo...")

    catalog_completo = await repo.buscar_catalogo_produtos()

    descricoes = [
        str(prod["descr"]).strip()
        for prod in catalog_completo
        if prod.get("descr")
    ]

    logger.info(f"[VETORES] Enviando {len(descricoes)} descrições para embeddings...")

    vetores_gerados = []

    tamanho_lote = 500

    for i in range(0, len(descricoes), tamanho_lote):

        lote_atual = descricoes[i:i + tamanho_lote]

        logger.info(
            f"[VETORES] Convertendo lote {i // tamanho_lote + 1} "
            f"({len(lote_atual)} itens)"
        )

        vetores_lote = await embeddings_model.aembed_documents(lote_atual)

        logger.info(f"[VETORES] Lote {i} convertido com sucesso")

        vetores_gerados.extend(vetores_lote)

    catalogo_vetorial = []

    for produto, vetor in zip(catalog_completo, vetores_gerados):

        catalogo_vetorial.append({
            "cpro": produto["cpro"],
            "descr": produto["descr"],
            "qtde_vendida": float(produto.get("qtde_vendida") or 0.0),
            "cemp": str(produto["cemp"]).strip(),
            "vetor": vetor,
        })

    logger.info(f"Validando o embedding: {len(catalogo_vetorial)} registros")
    # ==========================================
    # SALVA CACHE BINÁRIO
    # ==========================================
    with open(ARQUIVO_VETORES_CACHE, "wb") as f:
        pickle.dump(catalogo_vetorial, f)

    # ==========================================
    # SALVA DATA DA GERAÇÃO
    # ==========================================
    with open(ARQUIVO_CONTROLE_CACHE, "w") as f:
        f.write(hoje)

    logger.info(
        f"[VETORES] ✅ Cache atualizado com sucesso. "
        f"Total registros: {len(catalogo_vetorial)}"
    )

    return catalogo_vetorial

# --- FUNÇÃO AUXILIAR ASSÍNCRONA PARA PROCESSAR UM ÚNICO ITEM ---
async def processar_produto_paralelo(item, catalogo_empresa, empresa_atual, permitir_outros=False):
    """Executa a busca vetorial por matriz e a decisão da LLM concorrentemente por item."""
    nome_solicitado = item["name"]
    
    # 1. Transforma o texto solicitado em vetor matemático
    vetor_pedido = await embeddings_model.aembed_query(nome_solicitado)
    
    # 2. Converte os vetores da empresa em uma matriz Numpy para cálculo ultra-rápido
    vetores_banco = np.array([prod["vetor"] for prod in catalogo_empresa])

    similaridades_embedding = np.dot(vetores_banco, vetor_pedido)

    similaridades = similaridades_embedding.copy()
    
    # 3. Aplica o peso comercial logarítmico baseado nas quantidades vendidas
    for idx, prod in enumerate(catalogo_empresa):
        qtd = float(prod["qtde_vendida"] or 0)
        if qtd > 0:
            similaridades[idx] += np.log1p(qtd) * 0.02
            
    # Filtra e captura os 15 melhores índices
    indices_top = np.argsort(similaridades)[-15:][::-1]

    melhor_embedding = float(similaridades_embedding.max())

    LIMIAR_PADRAO = 0.60
    LIMIAR_FLEXIVEL = 0.55

    limiar = (LIMIAR_FLEXIVEL if melhor_embedding < LIMIAR_PADRAO else LIMIAR_PADRAO)
    
    pool_reduzido = []
    for idx in indices_top:
        score_embedding = float(similaridades_embedding[idx])
        score_final = float(similaridades[idx])

        if score_embedding < limiar:
            continue

        prod_vetor = catalogo_empresa[idx]

        pool_reduzido.append({
            "cpro": prod_vetor["cpro"],
            "descr": prod_vetor["descr"],
            "cemp": prod_vetor["cemp"],
            "status_estoque": "",
            "historico_saida": f"{int(prod_vetor['qtde_vendida'])} unidades vendidas",
            "score_embedding": round(score_embedding,4),
            "score_final": round(score_final,4)
        })

    
        # logger.info(f"Mostrando os pools reduzidos encontrados {pool_reduzido}")

    if(len(pool_reduzido) == 0):
        return {
            "id": "N/A", 
            "descr": f"{nome_solicitado} (Não encontrado na Empresa {empresa_atual})", 
            "quantidade": item["quantity"], 
            "source": "catalogo", 
            "status_estoque": "",
            "status": "normal",
        }

    pool_formatado = json.dumps(pool_reduzido, ensure_ascii=False, default=str)

    prompt = f"""
Você é o especialista em inteligência de catálogo da Fabesul.

Sua missão é identificar o produto do catálogo que representa comercialmente o item solicitado pelo cliente.

Seu objetivo principal é encontrar o MELHOR produto equivalente existente no catálogo.

Somente retorne found=false quando realmente não existir nenhum candidato compatível.

=========================================================
PRODUTO SOLICITADO PELO CLIENTE
=========================================================

{nome_solicitado}

=========================================================
EMPRESA
=========================================================

{empresa_atual}

REGRA ESPECIAL:

Quando a empresa for 01, é permitido utilizar produtos das empresas 01 e 05.

Para qualquer outra empresa utilize somente os produtos da própria empresa.

=========================================================
CANDIDATOS ENCONTRADOS
=========================================================

{pool_formatado}

=========================================================
PROCESSO DE DECISÃO
=========================================================

PASSO 0 — NORMALIZAÇÃO

Antes de comparar os produtos, normalize mentalmente as descrições.

Considere equivalentes as abreviações comerciais.

Exemplos:

QDRO = QUADRO

P/ = PARA

PRT = PRETO

AZ = AZUL

VD = VERDE

VM = VERMELHO

BCO = BRANCO

UN = UNIDADE

UNI = UNIDADE

UNID = UNIDADE

ESP = ESPIRAL

FLS = FOLHAS

CX = CAIXA

PCT = PACOTE

RL = ROLO

LT = LATA

REF = REFERÊNCIA

Ignore:

• pontuação

• hífens

• barras

• ordem das palavras

• letras maiúsculas/minúsculas

Exemplo:

MARCADOR P/ QDRO BRANCO COR PRT

é equivalente a

Marcador para Quadro Branco Preto

=========================================================

PASSO 1 — IDENTIFICAR A CATEGORIA

Primeiro identifique qual é a categoria principal do produto.

Exemplos:

Marcador para quadro branco

Caneta

Caderno

Detergente

Flanela

Copo

Livro Ata

Livro Protocolo

Vassoura

Se a categoria for diferente,
NÃO escolha o candidato.

Exemplos proibidos:

Caneca → Copo

Caneca → Garrafa

Marcador → Caneta

Detergente → Desinfetante

Papel → Plástico

Livro Ata → Livro Protocolo

Chapa → Cabo

=========================================================

PASSO 2 — RECONHECER SINÔNIMOS

Considere equivalentes comerciais.

Exemplos:

Flanela

=

Pano Multiuso

Pano Perfex

Panex

Inseticida

=

Raid

Baygon

SBP

Sayer

Copo de Água

=

Copo Descartável

Ignore diferenças de marca quando forem o mesmo produto.

Exemplos:

Ypê

Limpol

Bombril

Brw

Jocar

Pilot

Compactor

=========================================================

PASSO 3 — VALIDAR ATRIBUTOS IMPORTANTES

Após validar a categoria compare:

cor

litragem

gramagem

peso

quantidade de folhas

espessura

comprimento

embalagem

modelo

Os atributos devem ser compatíveis.

Exemplos:

96 folhas

não deve virar

48 folhas

450ml

não deve virar

5 litros

Marcador Preto

não deve virar

Marcador Azul

caso exista um Preto disponível.

=========================================================

PASSO 4 — REGRA DE CONTINGÊNCIA

Caso não exista exatamente o tamanho solicitado,
mas todos os candidatos pertençam à mesma categoria,
escolha o tamanho comercial mais próximo.

Exemplos:

Pedido

Inseticida 450ml

Catálogo

390ml

400ml

Escolha o mais próximo.

Esta regra NÃO pode ser utilizada para trocar categorias diferentes.

=========================================================

PASSO 5 — SCORE

Cada candidato possui dois scores.

score_embedding

Representa a similaridade semântica.

score_final

Representa a similaridade semântica ajustada pelo histórico comercial.

Sempre utilize score_final como principal critério técnico.

Quanto maior o score_final,
maior a prioridade do candidato.

=========================================================

PASSO 6 — HISTÓRICO COMERCIAL

historico_saida representa o número de unidades vendidas.

Quando dois ou mais candidatos forem comercialmente equivalentes,
prefira SEMPRE o produto com maior histórico de vendas.

O histórico representa o produto mais utilizado pelos clientes.

Nunca escolha um produto semanticamente muito pior apenas porque vende mais.

Mas entre candidatos equivalentes,
o histórico deve ser utilizado como fator decisivo.

=========================================================

PASSO 7 — PRODUTOS GENÉRICOS

Quando o cliente informar apenas o nome genérico do produto,
sem especificar marca,
modelo,
cor,
tamanho
ou embalagem,

escolha o produto com maior score_final.

Caso existam vários candidatos semelhantes,
prefira o maior histórico de vendas.

=========================================================

PASSO 8 — SEGURANÇA

Retorne found=false SOMENTE quando:

• nenhum candidato pertencer à mesma categoria

ou

• existir incompatibilidade evidente entre o pedido e todos os candidatos.

Não seja excessivamente conservador.

Se houver um candidato claramente equivalente,
retorne found=true.

Evite falso negativo.

Seu objetivo é localizar produtos equivalentes existentes no catálogo.

=========================================================
RETORNO
=========================================================

Responda SOMENTE utilizando o JSON definido pelo schema.

Não escreva explicações.

Não escreva comentários.

Não escreva markdown.

Não escreva texto adicional.
"""    
    response = await mapper_llm.ainvoke(prompt)
    
    if response.matches and response.matches[0].found:
        m = response.matches[0]
        produto_principal = {
            "id": int(m.matched_id), 
            "descr": m.matched_name, 
            "quantidade": item["quantity"], 
            "source": "catalogo",
            "status_estoque": "",
            "status": "normal",
        }

        if not permitir_outros:
            return produto_principal

        ids_alternativos = set()
        produtos_alternativos = []
        for candidato in pool_reduzido:
            id_candidato = str(candidato["cpro"])
            if id_candidato == str(m.matched_id) or id_candidato in ids_alternativos:
                continue

            ids_alternativos.add(id_candidato)
            produtos_alternativos.append({
                "id": int(candidato["cpro"]),
                "descr": candidato["descr"],
                "quantidade": item["quantity"],
                "source": "catalogo",
                "status_estoque": "",
                "status": "alternativo",
            })

            if len(produtos_alternativos) == 3:
                break

        return [produto_principal] + produtos_alternativos
    else:
        return {
            "id": "N/A", 
            "descr": f"{nome_solicitado} (Não encontrado na Empresa {empresa_atual})", 
            "quantidade": item["quantity"], 
            # "preco": 0.0, 
            "source": "catalogo", 
            "status_estoque": "",
            "status": "normal",
            "score_embedding": round(score_embedding,4)
            # "disp": 0,
            # "cemp": empresa_atual
        }


# --- NÓ PRINCIPAL DO GRAFO ---
async def match_catalog_node(state: AgentState):
    """
    Passo 4 do Grafo: Busca Semântica Avançada Concorrente.
    Filtra os produtos pela empresa e dispara as requisições em paralelo para otimização de tempo.
    """
    if not state["pending_items"]: 
        return state
    
    empresa_atual = str(state.get("cemp", "01")).strip().zfill(2)
    
    logger.info(f"🔌 [ESTEIRA: CATÁLOGO] Iniciando busca semântica para {len(state['pending_items'])} itens na base de dados...")
    
    # Carrega ou monta o cache global único
    base_mestre = await carregar_ou_criar_cache_vetorial()
    
    # Filtro em memória da empresa ativa
    if empresa_atual == "01":
        catalogo_empresa = [
            prod for prod in base_mestre
            if prod["cemp"].strip().zfill(2) in ["01", "05"]
        ]
    else:
        catalogo_empresa = [
            prod for prod in base_mestre
            if prod["cemp"].strip().zfill(2) == empresa_atual
        ]
    
    if not catalogo_empresa:
        logger.info(f"└───> ✨ [CATÁLOGO] Nenhum produto localizado no cache para a empresa {empresa_atual}")
        return state

    logger.info(f"└───> ✨ [CATÁLOGO] Analisando produtos...")

    permitir_outros = state.get("outros", False) is True and not state.get("contract_pool", [])

    tarefas = [
        processar_produto_paralelo(
            item,
            catalogo_empresa,
            empresa_atual,
            permitir_outros=permitir_outros,
        )
        for item in state["pending_items"]
    ]
    
    # Dispara a concorrência geral para a OpenAI
    found_in_catalog = await asyncio.gather(*tarefas)
    
    logger.info("└───> ✨ [CATÁLOGO] Busca semântica e viés comercial concluídos.")

    resultados_catalogo = []
    for resultado in found_in_catalog:
        if isinstance(resultado, list):
            resultados_catalogo.extend(resultado)
        else:
            resultados_catalogo.append(resultado)

    return {"pending_items": [], "final_results": state["final_results"] + resultados_catalogo}