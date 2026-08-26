from fastapi import APIRouter, HTTPException, File, UploadFile
import json
import os
import shutil
from decimal import Decimal
from app.utils.logger import logger_api


# Importa o grafo compilado exatamente com o nome que você definiu
from app.excel.fluxo_excel import app_flow

router = APIRouter()

@router.post("/processar-arquivo")
async def processar_orcamento_arquivo(
    file: UploadFile = File(..., description="Arquivo de pedido (.txt ou .pdf)")
):
    TEMP_DIR = os.path.join(os.getcwd(), "temp_uploads")
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 2. Define o caminho do arquivo apontando para essa pasta segura
    temp_file_path = os.path.join(TEMP_DIR, file.filename)
    
    try:
        logger_api.info(f"=============================== [Iniciando novo Processo] ===============================")
        logger_api.info(f"🚀 [START] Novo arquivo recebido: {file.filename}")

        # 1. OBRIGATÓRIO: Salva o arquivo fisicamente no disco para o 'no_extrator_dados' conseguir ler
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Monta o payload inicial respeitando sua DataProcessingState
        # Passamos apenas o file_path, o resto o grafo vai preencher
        input_data = {
            "file_path": temp_file_path,
            "extracted_data": None,
            "generated_code": None,
            "execution_result": None,
            "error_message": None,
            "retry_count": 0,
            "final_excel_path": None
        }
        
        # 3. Dispara a esteira do LangGraph que você construiu
        resultado_grafo = await app_flow.ainvoke(input_data)

        # 4. Captura os resultados finais gerados pelos nós
        dados_finais = resultado_grafo.get("execution_result")
        excel_gerado = resultado_grafo.get("final_excel_path")
        erro_no_grafo = resultado_grafo.get("error_message")
        
        if erro_no_grafo:
             raise Exception(f"O Grafo falhou após retentativas: {erro_no_grafo}")
        
        logger_api.info(f"🏁 [END] Processo concluído com sucesso para o Arquivo: {file.filename}")
        logger_api.info(f"=============================== [Finalizando Processo] ===============================")

        # 5. Retorna a resposta com o caminho do Excel
        return {
            "status": "sucesso",
            "arquivo_processado": file.filename,
            "produtos_mapeados": dados_finais,
            "download_excel_path": excel_gerado  # Retorna o caminho salvo pelo 'no_gerador_excel'
        }
        
    except Exception as e:
        logger_api.info(f"❌ ERRO CRÍTICO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no processamento do arquivo: {str(e)}")
        
    finally:
        # 6. Limpeza: apaga o arquivo bruto de entrada do disco para não lotar o servidor
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
@router.get("/online-teste")
def online():
    logger_api.info("➔ Alguém bateu no endpoint /online!")
    return {
        "status": "online"
    }