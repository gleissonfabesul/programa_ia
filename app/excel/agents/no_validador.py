from langgraph.graph import END
from app.excel.estado_excel import DataProcessingState
from typing import Dict

def validador_router(state: DataProcessingState):
    print("--- [BLOCO 4] TESTANDO E VALIDANDO O RESULTADO ---")
    
    # Se houver erro e ainda não estourou o limite de 3 tentativas, joga de volta para o Coder (Bloco 2)
    if state.get("error_message") and state.get("retry_count", 0) < 3:
        print(f"-> Validação Falhou! Erro encontrado: {state['error_message']}. Direcionando para RE-PROCESSAMENTO.")
        return "coder"
    
    # Se houver erro mas já tentou 3 vezes, encerra o fluxo para não entrar em loop infinito
    elif state.get("error_message"):
        print("-> Validação Falhou repetidamente. Limite de tentativas atingido. Encerrando com Erro.")
        return END
        
    # Se não houver erro, avança para gerar o Excel
    print("-> Validação com Sucesso! Avançando para a geração do arquivo final.")
    return "excel_generator"