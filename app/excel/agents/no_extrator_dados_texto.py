from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from app.excel.estado_excel import DataProcessingState
from typing import Dict
from app.configs.confgLang import excel_llm
from app.utils.logger import logger_api


def product_extractor_agent_node(state: DataProcessingState) -> Dict:
    print("--- [BLOCO 1.5] EXTRAINDO OS DADOS DO ARQUIVO")
    
    # Recebe a lista de páginas físicas do PDF
    paginas = state["extracted_data"]
    produtos_totais = []

    logger_api.info(f"-> Arquivo contém {len(paginas)} páginas. Iniciando extração segura...")
    
    for i, pagina in enumerate(paginas):
        print(f"-> Analisando página {i+1}...")
        
        prompt = f"""Você é um especialista em reconstruir dados de tabelas corrompidas.
        Extraia TODOS os produtos desta página.
        
        Regras RIGOROSAS (Preste muita atenção ao que NÃO pegar):
        1. Código: O código real do produto (maior número, ex: 134517). 
           - IGNORE colunas de prazo de entrega (números soltos como 15, 10, 30).
           - IGNORE sequenciais de item (1, 2, 40, 41).
        2. Nome do Produto: Deve ser um item descritivo (ex: LIXEIRA, SABONETE). 
           - NUNCA capture nomes de marcas isoladas (ex: MARTINS, BIC, ELGIN, PIMACO) como se fossem o nome do produto.
        3. Quantidade: O valor numérico. Se não houver, retorne 0.
        4. Valor do Produto: Identifique o valor unitário como float.
        5. Unidade de Medida: Identifique a sigla (ex: CX, PE, GL, UN).
        
        Texto da Página:
        ---
        {pagina}
        ---
        """
        
        resposta = excel_llm.invoke([
            SystemMessage(content="Você é um especialista em dados. Ignore marcas isoladas e prazos de entrega."),
            HumanMessage(content=prompt)
        ])
        
        if hasattr(resposta, "produtos") and resposta.produtos:
            lista_parcial = [produto.model_dump() for produto in resposta.produtos]
            produtos_totais.extend(lista_parcial)

    # Aplica a sua validação centralizada
    produtos_finais = aplicar_regras_validacao(produtos_totais)
    
    logger_api.info(f"✅ Sucesso! {len(produtos_finais)} produtos extraídos no total.")

    return {
        "execution_result": produtos_finais,
        "error_message": None
    }

def aplicar_regras_validacao(lista_produtos: list) -> list:
    produtos_validados = []
    
    for item in lista_produtos:
        # Garante que código seja string e limpa lixo
        codigo = str(item.get("codigo", "")).strip()
        
        # Garante que quantidade seja float (default 0.0)
        try:
            qtd = float(item.get("quantidade", 0.0))
        except (ValueError, TypeError):
            qtd = 0.0
            
        # Garante que valor seja float (default 0.0)
        try:
            valor = float(item.get("valor", 0.0))
        except (ValueError, TypeError):
            valor = 0.0

        produtos_validados.append({
            "nome": str(item.get("nome", "PRODUTO SEM NOME")).strip(),
            "codigo": codigo,
            "quantidade": qtd,
            "unidade_medida": str(item.get("unidade_medida", "")).strip(),
            "valor": valor
        })
        
    return produtos_validados




# def product_extractor_agent_node(state: DataProcessingState) -> Dict:
#     print("--- [BLOCO 1.5] EXTRAINDO DADOS ESTRUTURADOS COM O NOVO MODELO ---")
    
#     texto_bruto = state["extracted_data"]

#     print(texto_bruto)

#     prompt = f"""Você é um especialista em estruturação de dados fiscais e de suprimentos.
#     Analise o texto bruto abaixo e extraia TODOS os produtos presentes nele.
    
#     Regras RIGOROSAS de Extração:
#     1. Nome: A descrição detalhada do produto.
#     2. Código: O código real de identificação do produto (geralmente tem de 4 a 6 dígitos). 
#        - ATENÇÃO: Se a linha começar com um número pequeno sequencial (ex: 1, 2, 40) seguido de um número maior (ex: 134517), o MAIOR é o código. 
#        - Mas se a linha começar direto com o código longo (ex: 154911, 15397, 8013), capture ele normalmente!
#        - o Código pode vir de uma coluna chamada Código, Item e ela deve conter um range de numero entre 1 a 6
#     3. Quantidade: O valor numérico da quantidade. Se não houver NENHUMA quantidade explícita na linha para aquele produto, retorne OBRIGATORIAMENTE 0 (zero).
#     4. Unidade de Medida: Identifique a sigla (ex: CX, PE, GL, UN, LI).
#     5. Valor do Produto: Identifique o valor do produto.
    
#     Texto Bruto do Documento:
#     ---
#     {texto_bruto}
#     ---
#     """
    
#     # A resposta já volta como o objeto TabelaExcel perfeitamente tipado!
#     resposta = excel_llm.invoke([
#         SystemMessage(content="Você é um agente focado em extração exata de entidades e produtos de documentos."),
#         HumanMessage(content=prompt)
#     ])

#     # Transformamos o objeto Pydantic em uma lista de dicionários limpa para o Pandas
#     # Vai gerar algo como: [{"nome": "CANETA", "codigo": "123", "quantidade": 2.0}, ...]
#     lista_produtos = [produto.model_dump() for produto in resposta.produtos]
    
#     print(f"✅ Sucesso! {len(lista_produtos)} produtos extraídos perfeitamente.")

#     # Enviamos direto para o execution_result (pulando o Coder e o Executor!)
#     return {
#         "execution_result": lista_produtos,
#         "error_message": None
#     }