from app.orcamento.estado_orcamento import AgentState
from app.configs.confgLang  import llm, repo
from app.utils.logger import logger
from app.repositories.repositorio_cliente import RepositorioCliente
from app.repositories.repositorio_produtos import RepositorioProdutos
from decimal import Decimal

async def inventory_node(state: AgentState):
    """Passo 5: Verifica o estoque e sugere similares se necessário."""
    validated_results = []

    logger.info(f"🔌 [ESTEIRA: ESTOQUE] Validando estoque")

    logger.info(f"└───> ✨ [ESTOQUE] Analisando produtos...")

    # logger.info(f"└───> ✨ [ESTOQUE] Iniciando analise de saldo disponivel dos produtos: {state['final_results']}")
    
    for item in state["final_results"]:
        if item["id"] == "N/A":
            validated_results.append(item)
            continue

        try:
            id_limpo = int(float(str(item["id"]).strip()))
        except Exception as e:
            logger.error(f"❌ Erro ao formatar ID do produto {item.get('descr')}: {str(e)}")
            validated_results.append(item)
            continue
        
        repositorio_cliente = RepositorioCliente()
        repositorio_produto = RepositorioProdutos()

        cliente = await repositorio_cliente.buscar_cliente(state["customer_id"])

        # dados_banco = await repo.buscar_produto_disp(id_limpo, state["cemp"])
        dados_banco = await repositorio_produto.buscar_preco_produto(state["cemp"], cliente.ccli, cliente.cate, cliente.contri, id_limpo)

        # logger.info(f"└───> ✨ [ESTOQUE] Dados buscados no banco {dados_banco}")

        if dados_banco:
            prod_real = dados_banco[0]
            estoque_atual = float(prod_real.get("Disp", 0))
            preco_atual = float(prod_real.get("PreCli") or 0.0)
        else:
            estoque_atual = 0.0
            preco_atual = 0.0
            
        try:
            qtd_solicitada = float(item["quantidade"])
        except:
            qtd_solicitada = 0.0

        if estoque_atual >= qtd_solicitada:
            item["status_estoque"] = "OK"
            validated_results.append(item)
        else:
            logger.warning(f"└───> ⚠️ [ESTOQUE] Sem estoque para {item['descr']}. Buscando similar...")
            
            similares = await repo.buscar_similares_com_estoque(item["descr"], state["cemp"])
            
            if similares:
                lista_cpros = [int(produto["cpro"]) for produto in similares]

            dados_banco = await repositorio_produto.buscar_precos_produtos(state["cemp"], cliente.ccli, cliente.cate, cliente.contri, lista_cpros)

            produtos_filtrados = [
                {
                    "cpro": int(produto["CPro"]),
                    "descr": str(produto["Descr"]),
                    "disp": int(produto["Disp"]),
                    "prect": Decimal(produto["Prein"])
                }
                for produto in dados_banco
            ]

            # logger.info(f"\n\n └───> ✨ [ESTOQUE] Similares ao produtos solicitado {produtos_filtrados} \n\n")
            
            if similares:
                prompt = f"""
                    Você é o assistente especialista em suprimentos B2B da Fabesul.
                    O cliente solicitou originalmente o item: '{item['descr']}'
                    No entanto, este item exato está indisponível. Sua missão é escolher o substituto ideal.

                    OPÇÕES DE PRODUTOS SIMILARES DISPONÍVEIS COM ESTOQUE REAL:
                    {produtos_filtrados}

                    RETORNO OBRIGATÓRIO (SIGA RIGOROSAMENTE):
                    Responda APENAS e estritamente com o número do 'cpro' do produto que você escolheu.
                    Não escreva justificativas, não crie blocos JSON, não coloque pontuação. Se nenhuma opção passar nas travas, responda apenas a palavra: FALSO
                    """
                
                escolha = await llm.ainvoke(prompt)

                cpro_escolhido = str(escolha.content).strip()

                if not cpro_escolhido or "FALSO" in cpro_escolhido.upper() or "N/A" in cpro_escolhido.upper():
                    item["status_estoque"] = "SEM ESTOQUE/REJEITADO"
                    validated_results.append(item)
                else:
                    substituto = next((x for x in similares if str(x.get('cpro')).strip() == cpro_escolhido), similares[0])
                    
                    validated_results.append({
                        "id": int(substituto["cpro"]), 
                        "descr": substituto["descr"],
                        "quantidade": item["quantidade"],
                        "source": f"Substituição (original: {item['id']})", 
                        "status_estoque": "SUBSTITUÍDO",
                        "status": item.get("status", "normal")
                    })
            else:
                item["status_estoque"] = "SEM ESTOQUE / SEM SIMILAR"
                validated_results.append(item)

    logger.info(f"└───> ✨ [ESTOQUE] Concluído.")
    logger.info("🔌 [ESTEIRA: ESTOQUE] Validação estoque dos produtos finalizado.")

    return {"final_results": validated_results}




# prompt = f"""
#                     Você é o assistente especialista em suprimentos B2B da Fabesul.
#                     O cliente solicitou originalmente o item: '{item['name']}'
#                     No entanto, este item exato está indisponível. Sua missão é escolher o substituto ideal.

#                     OPÇÕES DE PRODUTOS SIMILARES DISPONÍVEIS COM ESTOQUE REAL:
#                     {similares}

#                     REGRAS CRÍTICAS DE BLOQUEIO (ORDEM DE PRIORIDADE MÁXIMA):
#                     1. 🚨 TRAVA ABSOLUTA DE SACHÊS / MICRO-UNIDADES: 
#                        - É terminantemente PROIBIDO substituir um produto de peso doméstico ou industrial por sachês fracionados de recepção (Ex: Se o cliente pediu Açúcar 5KG ou 1KG, é PROIBIDO sugerir 'Açúcar Sachê 5g', pois a aplicação comercial é totalmente diferente).
                    
#                     2. 🔄 REGRA DE CONVERSÃO DE FRACIONAMENTO (QUILOS E LITROS):
#                        - Se o cliente solicitou um produto em embalagem grande (Ex: Açúcar 5KG, Alvejante 5L) e ele NÃO estiver disponível, você TEM PERMISSÃO para selecionar a embalagem menor correspondente para fracionamento (Ex: Açúcar 1KG ou Alvejante 1L), desde que seja o mesmo tipo de produto. 
#                        - NOTA: Não se preocupe com a quantidade multiplicada agora, o sistema Python ajustará o faturamento depois. Foque em dar o match no produto de 1KG/1L.

#                     3. 🚨 TRAVA DE VOLUMETRIA DURA PARA SACOS/COPOS/PAPEIS:
#                        - Para itens de consumo direto por tamanho (Ex: Saco de Lixo 15L, Copo 200ml), você NÃO PODE sugerir tamanhos gigantescos ou minúsculos (Ex: É PROIBIDO substituir Saco de 15L por Saco de 100L, ou Copo de 50ml por Copo de 200ml). Na ausência do tamanho exato desses itens, retorne FALSO.

#                     4. EQUIVALÊNCIA COMERCIAL: Dentre as opções válidas, escolha aquela que tiver o maior volume de vendas em 'historico_saida'.

#                     RETORNO OBRIGATÓRIO (SIGA RIGOROSAMENTE):
#                     Responda APENAS e estritamente com o número do 'cpro' do produto que você escolheu.
#                     Não escreva justificativas, não crie blocos JSON, não coloque pontuação. Se nenhuma opção passar nas travas, responda apenas a palavra: FALSO
#                     """
