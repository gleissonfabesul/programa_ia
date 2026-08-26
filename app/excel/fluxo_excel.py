from langgraph.graph import StateGraph, END
from app.excel.estado_excel import DataProcessingState

# Importamos apenas os 3 nós vivos
from app.excel.agents import (
    no_extrator_dados, 
    no_extrator_dados_texto, 
    no_gerador_excel
)

# 1. Cria o grafo
workflow = StateGraph(DataProcessingState)

# 2. Registra os nós
workflow.add_node("extractor", no_extrator_dados.no_extrator_dados)
workflow.add_node("product_agent", no_extrator_dados_texto.product_extractor_agent_node)
workflow.add_node("excel_generator", no_gerador_excel.excel_generator_node)

# 3. Fluxo de execução DIRETO e RÁPIDO
workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "product_agent")          # Lê o arquivo e manda pra IA
workflow.add_edge("product_agent", "excel_generator")    # IA estrutura dados e manda pro Pandas
workflow.add_edge("excel_generator", END)                # Pandas gera o Excel e fim!

# Compila o grafo
app_flow = workflow.compile()