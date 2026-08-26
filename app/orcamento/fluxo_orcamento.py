from langgraph.graph import StateGraph, END
from app.orcamento.estado_orcamento import AgentState
from app.orcamento.agents.no_extracao import extraction_node
from app.orcamento.agents.no_historico import match_history_node
from app.orcamento.agents.no_contrato import match_contract_node
from app.orcamento.agents.no_catalogo import match_catalog_node
from app.orcamento.agents.no_estoque import inventory_node

workflow = StateGraph(AgentState)

# Registra os nós importados
workflow.add_node("extraction", extraction_node)
workflow.add_node("match_history", match_history_node)
workflow.add_node("match_contract", match_contract_node)
workflow.add_node("match_catalog", match_catalog_node)
workflow.add_node("inventory_check", inventory_node)

# Define o roteamento
workflow.set_entry_point("extraction")
workflow.add_edge("extraction", "match_contract")
workflow.add_edge("match_contract", "match_history")
workflow.add_edge("match_history", "match_catalog")
workflow.add_edge("match_catalog", "inventory_check")
workflow.add_edge("inventory_check", END)

# Compilação global do Grafo para consumo externo
app = workflow.compile()