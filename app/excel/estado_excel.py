from typing import Dict, List, TypedDict, Optional, Any

class DataProcessingState(TypedDict):
    file_path: str                 # Caminho do arquivo de entrada bruto
    extracted_data: Optional[str]  # Dados brutos limpos ou JSON textualizado
    generated_code: Optional[str]  # Código Python gerado pela LLM
    execution_result: Optional[Any] # Resultado retornado da execução do código
    error_message: Optional[str]   # Mensagem de erro caso a execução falhe
    retry_count: int               # Contador de tentativas de correção
    final_excel_path: Optional[str]# Caminho do arquivo .xlsx gerado com sucesso