from app.orcamento.estado_orcamento import AgentState
from app.configs.confgLang  import extraction_llm, repo
from app.utils.logger import logger
import json

async def extraction_node(state: AgentState):
    """Passo 1: Extrai produtos e quantidades isolando dados técnicos."""

    logger.info("🤖 [AGENTE] Iniciando leitura e estruturação do pedido bruto...")

    prompt = f"""
        Você é um extrator inteligente de pedidos de compra B2B.

        O conteúdo recebido pode conter:
        - texto digitado pelo cliente
        - conteúdo OCR de PDF
        - planilhas Excel
        - tabelas
        - listas de produtos
        - textos administrativos
        - cabeçalhos
        - rodapés
        - telefones
        - emails
        - CNPJ
        - assinaturas

        Sua tarefa é:

        1. Identificar TODOS os produtos solicitados
        2. Extrair a quantidade correta de cada item
        3. Unificar itens vindos do TEXTO + ARQUIVO
        4. Ignorar informações administrativas
        5. Ignorar telefones, emails, endereços, CNPJ e cabeçalhos
        6. Considerar linhas de tabelas e planilhas como produtos válidos
        7. NÃO ignorar produtos apenas porque estão abaixo do primeiro bloco de texto
        8. Retornar SOMENTE produtos realmente solicitados

        Regras importantes:
        - Medidas como 500ml, 5kg, 200m, 180ml fazem parte da descrição
        - Quantidades pedidas normalmente aparecem como:
        - 10
        - 10un
        - 10 unidades
        - 4 pacotes
        - 2 caixas
        - Se existir nome + número em linha de tabela, considere como item válido
        - Remova duplicidades
        - Não invente produtos

        - Quando a quantidade não estiver explicitamente informada, considere quantidade = 1.
        - Nunca utilize códigos internos, códigos de barras, SKU, EAN ou números de referência como quantidade.
        - Em tabelas ou planilhas, identifique corretamente qual coluna representa a quantidade antes de extrair os itens.

        PEDIDO COMPLETO:
        {state['raw_request']}
        """

    res = await extraction_llm.ainvoke(prompt)
    pending = [{"name": m.product_name, "quantity": m.quantidade} for m in res.items]

    logger.info(f"??????????????? O que foi extraido pelo Agente ???????????????????????")
    logger.info(f"{pending}")
    
    history = await repo.buscar_historico_produtos(state["customer_id"], state["cemp"])
    contract = await repo.buscar_produtos_contrato(state["customer_id"], state["cemp"])

    json_pendentes = json.dumps(pending, ensure_ascii=False, separators=(',', ':'))
    # logger.info(f"🤖 [AGENTE] Itens identificados no pedido bruto: {json_pendentes}")
    
    logger.info("🤖 [AGENTE] Pedido estruturado com sucesso em formato JSON.")

    return {
        "pending_items": pending,
        "history_pool": history,
        "contract_pool": contract,
        "final_results": []
    }