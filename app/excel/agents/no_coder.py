from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.excel.estado_excel import DataProcessingState
from typing import Dict
from app.configs.confgLang import excel_llm
import re

def coder_node(state: DataProcessingState) -> Dict:
    print(f"--- [BLOCO 2] GERANDO CÓDIGO (Tentativa {state.get('retry_count', 0) + 1}) ---")
    
    dados_brutos = state["extracted_data"]
    contexto_erro = ""
    
    # Se já houve um erro anterior, passa o feedback para a LLM se corrigir
    if state.get("error_message"):
        contexto_erro = f"\n\nATENÇÃO: O código anterior falhou com o seguinte erro:\n{state['error_message']}\nPor favor, corrija o código para evitar este problema."

    prompt = f"""Baseado nos seguintes dados extraídos de um arquivo:
        ---
        {dados_brutos}
        ---

        Escreva um código em Python puro que filtre/processe esses dados e crie OBRIGATORIAMENTE uma lista de dicionários nativos chamada 'dados_finais'. 

        Regras estritas para a estrutura dos dados (Colunas do Excel):
        1. Cada dicionário na lista DEVE conter EXATAMENTE estas 3 chaves:
           - "nome": A descrição do produto.
           - "codigo": O código do produto (numérico).
           - "quantidade": A quantidade do produto. Se a quantidade não estiver explícita no texto, assuma o valor numérico 1.
        
        2. Exemplo do formato EXATO esperado: 
           dados_finais = [ {{"nome": "ROLETE EN.CA.EL(DISMAC/SHARP", "codigo": "15403", "quantidade": 1}} ]
        
        3. Use apenas tipos nativos do Python (strings, listas, dicionários, int, float) ou Pandas.
        4. NÃO utilize nenhuma classe externa, objetos customizados como 'MatchResult', 'MatchBatch' ou ferramentas de IA dentro do código gerado. O código deve ser puramente de manipulação de dados/texto.
        5. Retorne APENAS o código Python limpo, sem blocos de markdown de código (sem ```python).{contexto_erro}"""
    
    resposta = excel_llm.invoke([
        SystemMessage(content="Você é um Engenheiro de Dados especialista em Python que escreve apenas códigos limpos e funcionais."),
        HumanMessage(content=prompt)
    ])

    texto_gerado = ""

    # 1. Se for o objeto padrão com .content
    if hasattr(resposta, "content"):
        texto_gerado = resposta.content

    # 2. Se for um objeto com choices (OpenAI)
    elif hasattr(resposta, "choices") and resposta.choices:
        texto_gerado = resposta.choices[0].message.content

    # 3. Se for uma lista
    elif isinstance(resposta, list) and resposta:
        if hasattr(resposta[0], "content"):
            texto_gerado = resposta[0].content
        else:
            texto_gerado = str(resposta[0])

    # 4. Caso de segurança (converte o MatchBatch para string)
    else:
        texto_gerado = str(resposta)

    texto_gerado = re.sub(r"^```python\s*", "", texto_gerado, flags=re.IGNORECASE)
    texto_gerado = re.sub(r"^```\s*", "", texto_gerado, flags=re.IGNORECASE)
    texto_gerado = re.sub(r"\s*```$", "", texto_gerado, flags=re.IGNORECASE)
    texto_gerado = texto_gerado.strip()

    print(f"Código gerado:\n" + texto_gerado)

    print(f"Código gerado" + texto_gerado)
    
    return {
        "generated_code": texto_gerado,
        "retry_count": state.get("retry_count", 0) + 1
    }