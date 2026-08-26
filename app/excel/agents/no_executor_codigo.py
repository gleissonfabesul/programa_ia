from app.excel.estado_excel import DataProcessingState
from typing import Dict

class DynamicMatchResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def to_dict(self):
        return self.__dict__

def executor_node(state: DataProcessingState) -> Dict:
    print("--- [BLOCO 3] EXECUTANDO O CÓDIGO GERADO ---")
    codigo_string = state["generated_code"]
    
    # 2. Injetamos a nossa classe "falsa" como se fosse a original no escopo global
    escopo_global = {"MatchResult": DynamicMatchResult}
    escopo_local = {}
    
    try:
        # Executa a string de código. Se tiver "MatchResult(...)", o Python usa a nossa classe!
        exec(codigo_string, escopo_global, escopo_local)
        
        # 3. Tenta pegar os dados (a LLM pode ter chamado de dados_finais ou matches)
        dados = escopo_local.get("dados_finais") or escopo_local.get("matches") or escopo_global.get("matches")
        
        if dados is not None:
            # 4. Transforma os objetos mockados em dicionários limpos para o gerador de Excel
            dados_tratados = []
            for item in dados:
                if isinstance(item, DynamicMatchResult):
                    dados_tratados.append(item.to_dict())
                elif isinstance(item, dict):
                    dados_tratados.append(item)
                else:
                    dados_tratados.append({"resultado": str(item)})

            return {
                "execution_result": dados_tratados, 
                "error_message": None # Limpa erros anteriores se houver sucesso
            }
        else:
            return {"error_message": "O código executou com sucesso, mas esqueceu de criar a variável 'dados_finais' ou 'matches'."}
            
    except Exception as e:
        # Captura qualquer erro de sintaxe, NameError, KeyError, etc.
        return {"error_message": str(e)}