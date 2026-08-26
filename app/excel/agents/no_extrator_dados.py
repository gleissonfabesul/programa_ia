from app.excel.estado_excel import DataProcessingState
from typing import Dict
from app.utils.logger import logger_api
import os
import pdfplumber


def no_extrator_dados(state: DataProcessingState) -> Dict:
    logger_api.info(" [BLOCO 1] LENDO ARQUIVO", flush=True)
    caminho_arquivo = state["file_path"]
    
    if not os.path.exists(caminho_arquivo):
        raise FileNotFoundError(f"Arquivo não encontrado em: {caminho_arquivo}")
        
    extensao = os.path.splitext(caminho_arquivo)[1].lower()
    conteudo = []
    
    try:
        if extensao == ".txt":
            with open(caminho_arquivo, "r", encoding="utf-8", errors="replace") as f:
                conteudo = [f.read()]
                
        elif extensao == ".pdf":
            # A mágica do pdfplumber: ele lê o documento respeitando as colunas visuais
            with pdfplumber.open(caminho_arquivo) as pdf:
                for page in pdf.pages:
                    # layout=True é o segredo para extrair tabelas sem misturar as linhas
                    texto_pagina = page.extract_text(layout=True)
                    if texto_pagina and texto_pagina.strip():
                        conteudo.append(texto_pagina)
        else:
            raise ValueError(f"Formato {extensao} não suportado.")
            
        return {
            "extracted_data": conteudo,
            "retry_count": 0
        }
    except Exception as e:
        print(f"❌ Erro de leitura: {str(e)}", flush=True)
        return {"error_message": f"Erro de leitura: {str(e)}"}




# def no_extrator_dados(state: DataProcessingState) -> Dict:
#     print("--- [BLOCO 1] LENDO ARQUIVO FÍSICO (TXT/PDF) ---")
#     caminho_arquivo = state["file_path"]
    
#     if not os.path.exists(caminho_arquivo):
#         raise FileNotFoundError(f"Arquivo não encontrado em: {caminho_arquivo}")
        
#     extensao = os.path.splitext(caminho_arquivo)[1].lower()
#     conteudo_bruto = ""
    
#     # 1. Leitura dinâmica baseada na extensão do arquivo
#     if extensao == ".txt":
#         with open(caminho_arquivo, "r", encoding="utf-8") as f:
#             conteudo_bruto = f.read()
            
#     elif extensao == ".pdf":
#         reader = PdfReader(caminho_arquivo)
#         paginas_texto = []
#         for page in reader.pages:
#             texto_pagina = page.extract_text()
#             if texto_pagina:
#                 paginas_texto.append(texto_pagina)
#         conteudo_bruto = "\n".join(paginas_texto)
        
#     else:
#         raise ValueError(f"Formato de arquivo {extensao} não suportado. Envie .txt ou .pdf")
        
#     return {
#         "extracted_data": conteudo_bruto,
#         "retry_count": 0
#     }

