from app.orcamento.estado_orcamento import AgentState
from app.configs.confgLang import mapper_llm
from app.utils.logger import logger

async def match_contract_node(state: AgentState):
    """Passo 3: Busca inteligente no Contrato com controle estável via Python."""
    if not state["pending_items"]: 
        return state
    
    pool_contrato = state.get("contract_pool", [])
    total_pool = len(pool_contrato)

    logger.info(f"🔌 [ESTEIRA: CONTRATO] Validando {len(state['pending_items'])} itens pendentes nas tabelas de preço fixo...")

    # 🚨 TRAVA DE SEGURANÇA ABSOLUTA: 
    # Se o cliente não tem nenhum item sob contrato no banco, não chama a IA. Evita alucinações e economiza tokens.
    if total_pool == 0:
        logger.info("└───> ℹ️ [CONTRATO] Pool de contrato vazio para este cliente. Avançando itens pendentes...")
        return {
            "pending_items": state["pending_items"], 
            "final_results": state["final_results"]
        }

    nomes_pendentes = [i["name"] for i in state["pending_items"]]
    
    prompt = f""" Você deve mapear os itens solicitados pelo cliente para os produtos disponíveis no CONTRATO de fornecimento. REGRA ABSOLUTA DE PRIORIDADE DO CONTRATO: 1. O CONTRATO é a fonte prioritária e obrigatória para o atendimento dos produtos solicitados. 2. SE EXISTIR NO CONTRATO um produto que seja comercialmente equivalente ao produto solicitado pelo cliente: - obrigatoriamente utilize o produto do CONTRATO; - retorne found=True; - informe o produto do CONTRATO correspondente; - NÃO procure, sugira ou selecione outro produto fora do CONTRATO; - NÃO substitua o produto do CONTRATO por outro produto encontrado em outra fonte. 3. SOMENTE quando NÃO EXISTIR nenhum produto comercialmente equivalente no CONTRATO, o item poderá ser considerado não encontrado no contrato (found=False), permitindo que uma etapa posterior procure o produto em outra fonte. 4. Portanto: CONTRATO ENCONTRADO = SEMPRE USAR O CONTRATO. CONTRATO NÃO ENCONTRADO = pode procurar em outra fonte posteriormente. DIRETRIZES DE EQUIVALÊNCIA COMERCIAL: 1. "Água Sanitária" e "Alvejante" são sinônimos exatos. Se o cliente pediu "Água Sanitária" e no contrato constar "Alvejante" com a mesma volumetria, considere MATCH (found=True). 2. IGNORE marcas, siglas ou especificações adicionais trazidas no pedido quando elas não alterarem a finalidade comercial do produto. Exemplos: - marcas; - siglas; - fabricantes; - especificações químicas adicionais; - códigos de referência. Exemplo: "Água Sanitária Cloro Ativo 2 a 2.5% 5 Litros" pode casar com: "Alvejante 5L" desde que o produto tenha a mesma aplicação comercial e volumetria compatível. 3. TRAVA DE VOLUMETRIA: A volumetria/tamanho deve ser respeitada. Exemplos: - 5 Litros NÃO pode casar com 1 Litro. - 500ml NÃO pode casar com 5 Litros. - 300ml NÃO pode casar automaticamente com 500ml. - 40g NÃO pode casar automaticamente com 200g. 4. O produto deve manter a mesma aplicação comercial. Exemplos proibidos: - Caneca → Garrafa - Caneca → Copo - Chapa → Cabo - Vassoura → Rodo - Papel → Plástico 5. NÃO escolha um produto apenas porque as palavras são semanticamente parecidas. 6. A equivalência deve considerar principalmente: - tipo do produto; - finalidade/aplicação; - tamanho/volumetria; - unidade de medida; - características essenciais. 7. Quando houver mais de um produto equivalente no CONTRATO: - escolha o produto do contrato que tenha maior correspondência com o pedido; - NÃO procure produtos fora do contrato; - se houver empate ou dúvida relevante, retorne found=False. 8. Se existir um produto claramente equivalente no CONTRATO, NÃO retorne found=False apenas porque a descrição do contrato é diferente da descrição do cliente. Exemplo: Cliente: "Cola Branca Liquida 40g" Contrato: "Cola Branca 40G Maxi Cola 436" Resultado: found=True O produto do CONTRATO deve ser utilizado. 9. Outro exemplo: Cliente: "Saponáceo Cremoso 300 Gr" Contrato: "Saponáceo Cremoso 300Ml Limão Class Sleeve" Avalie cuidadosamente a unidade de medida e a equivalência comercial. NÃO descarte automaticamente apenas porque existem diferenças de marca, sabor, fragrância ou descrição comercial. Porém, se a diferença de unidade/tamanho representar um produto diferente, retorne found=False. 10. REGRA DE SEGURANÇA: Se houver dúvida real sobre a equivalência comercial, retorne found=False. Nunca invente correspondências. Nunca force um match. Nunca escolha um produto fora do CONTRATO quando existe um equivalente dentro dele. PROCESSO OBRIGATÓRIO: Para CADA item de RESTANTES SOLICITADOS: ETAPA 1: Procure primeiro no CONTRATO DISPONÍVEL. ETAPA 2: Verifique se existe um produto comercialmente equivalente. ETAPA 3: Se existir: found=True utilize EXATAMENTE o produto encontrado no CONTRATO. ETAPA 4: Somente se NÃO existir: found=False IMPORTANTE: Você NÃO deve procurar produtos fora do CONTRATO nesta etapa. Esta etapa serve EXCLUSIVAMENTE para identificar quais produtos solicitados possuem correspondência no CONTRATO. RESTANTES SOLICITADOS (Cliente): {nomes_pendentes} CONTRATO DISPONÍVEL (Banco): {pool_contrato} """

    logger.info(f"└───> ✨ [CONTRATO] Analisando produtos...")
    response = await mapper_llm.ainvoke(prompt)
    logger.info("└───> ✨ [CONTRATO] Concluído.")
    
    # Armazena as respostas da IA mapeadas pelo termo original
    matches_ia = {m.original_query.lower().strip(): m for m in response.matches}
    
    found = []
    still_pending = []
    nao_encontrados = []
    
    for item in state["pending_items"]:
        match_llm = matches_ia.get(item["name"].lower().strip())
        
        if match_llm and match_llm.found:
            id_mapeado = str(match_llm.matched_id).strip()
            
            # 🚨 DUPLA TRAVA: Garante que o ID retornado pela IA de fato existe no contract_pool vindo do ERP
            existe_no_pool = any(str(x.get('cpro')).strip() == id_mapeado for x in pool_contrato)
            
            if existe_no_pool:
                found.append({
                    "id": int(match_llm.matched_id), 
                    "descr": match_llm.matched_name, 
                    "quantidade": item["quantity"], 
                    "source": "contrato",
                    "status_estoque": "",
                    "status": "normal",
                })
                continue  # Item resolvido pelo contrato, vai para o próximo
        
        # Se a IA não achar match, ou tentar alucinar um ID inexistente na lista real, continua pendente
        nao_encontrados.append({
            "id": "N/A",
            "descr": match_llm.matched_name,
            "quantidade": item["quantity"],
            "source": "contrato",
            "status_estoque": "",
            "status": "normal",
        })
    
    logger.info("🔌 [ESTEIRA: CONTRATO] Validação de tabelas de contrato finalizada.")
            
    return {
        "pending_items": still_pending, 
        "final_results": state["final_results"] + found + nao_encontrados
    }