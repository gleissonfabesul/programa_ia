from app.orcamento.estado_orcamento import AgentState
from app.configs.confgLang import mapper_llm
from app.utils.logger import logger

async def match_history_node(state: AgentState):
    """Passo 2: Busca no Histórico carregando a quantidade com controle estável via Python."""
    if not state["pending_items"]: 
        return state

    pool_historico = state.get("history_pool", [])
    total_pool = len(pool_historico)

    logger.info(f"🔌 [ESTEIRA: HISTÓRICO] Cruzando {len(state['pending_items'])} itens com compras anteriores...")

    # 🚨 TRAVA DE SEGURANÇA ABSOLUTA: 
    # Se o cliente não tem histórico de compras na base, não chama a IA. Evita alucinações e economiza tokens!
    if total_pool == 0:
        logger.info("└───> ℹ️ [HISTÓRICO] Pool de histórico vazio para este cliente. Pulando direto para o próximo nó...")
        return {
            "pending_items": state["pending_items"], 
            "final_results": state["final_results"]
        }

    nomes_pendentes = [i["name"] for i in state["pending_items"]]
    prompt = f"""
            Você é um especialista em identificação de produtos comprados anteriormente por um cliente.

            Sua missão é verificar se os produtos solicitados já foram comprados anteriormente.

            PRODUTOS SOLICITADOS:
            {nomes_pendentes}

            HISTÓRICO DE COMPRAS:
            {pool_historico}

            REGRAS ABSOLUTAS (OBRIGATÓRIAS)

            1. O tipo principal do produto deve ser o mesmo.

            Exemplos proibidos:

            Caneca → Garrafa
            Caneca → Copo
            Copo → Taça
            Chapa → Cabo
            Vassoura → Rodo
            Detergente → Desinfetante

            2. Ignore diferenças de marca.

            Exemplo:

            Detergente Ypê
            Detergente Limpol

            podem ser equivalentes.

            3. Ignore pequenas diferenças de descrição comercial.

            Exemplo:

            Detergente Neutro

            Detergente Neutro Premium

            4. Quando existir litragem, gramagem ou embalagem,
            ela deve ser compatível.

            Exemplo:

            5L ≠ 500ml

            20kg ≠ 1kg

            100 unidades ≠ 10 unidades

            5. Se houver qualquer dúvida,
            retorne found=False.

            Nunca tente adivinhar.

            6. Nunca escolha apenas porque a descrição parece parecida.

            7. Não considere apenas palavras isoladas.

            Exemplo:

            "Chapa Galvanizada"

            NÃO é equivalente a

            "Cabo Chapa de Aço"

            Apesar de ambas possuírem a palavra "Chapa".

            Sempre analise o significado completo da descrição.

            8. Caso dois produtos compartilhem apenas uma palavra em comum,
            mas possuam aplicações diferentes,
            retorne found=False.

            RETORNE SOMENTE O JSON DEFINIDO PELO SCHEMA.
            """

    logger.info(f"└───> ✨ [HISTÓRICO] Analisando produtos...")
    response = await mapper_llm.ainvoke(prompt)
    logger.info("└───> ✨ [HISTÓRICO] Concluído.")
    
    matches_ia = {m.original_query.lower().strip(): m for m in response.matches}
    found, still_pending = [], []
    
    for item in state["pending_items"]:
        match_llm = matches_ia.get(item["name"].lower().strip())
        
        # Só valida se a IA encontrou E se o ID mapeado de fato pertence ao pool real trazido do banco
        if match_llm and match_llm.found:
            id_mapeado = int(match_llm.matched_id)
            
            # Dupla trava: verifica se o ID inventado pela IA existe fisicamente na lista do ERP
            existe_no_pool = any(str(x.get('cpro')) == str(id_mapeado) for x in pool_historico)
            
            if existe_no_pool:
                found.append({
                    "id": id_mapeado, 
                    "descr": match_llm.matched_name, 
                    "quantidade": item["quantity"], 
                    "source": "historico",
                    "status_estoque": "",
                    "status": "normal",
                })
                continue
        
        # Se a IA disser que não achou, ou se tentar inventar um ID que não tá no pool, continua pendente
        still_pending.append(item)
            
    logger.info("🔌 [ESTEIRA: HISTÓRICO] Varredura de histórico finalizada.")
    return {
        "pending_items": still_pending, 
        "final_results": state["final_results"] + found
    }