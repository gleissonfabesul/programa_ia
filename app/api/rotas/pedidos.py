from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.logger import logger
from app.orcamento.fluxo_orcamento import app  # Importa o grafo pronto
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from app.orcamento.fluxo_orcamento import app as agent_app
from app.utils.extrator import extrair_texto_de_arquivo
import json
from decimal import Decimal

router = APIRouter()

class PedidoRequest(BaseModel):
    customer_id: int
    raw_request: str
    cemp: str
    outros: bool = False

@router.post("/processar-orcamento")
async def processar_orcamento(payload: PedidoRequest):
    try:
        input_data = {
            "cemp": payload.cemp,
            "customer_id": payload.customer_id,
            "outros": payload.outros,
            "raw_request": payload.raw_request
        }
        logger.info(f"=============================== [Iniciando novo Processo] ===============================")
        logger.info(f"🚀 [START] Novo orçamento recebido (Empresa: {payload.cemp} | Cliente: {payload.customer_id})")

        resultado_grafo = await app.ainvoke(input_data)

        dados_finais = resultado_grafo.get("final_results", resultado_grafo)
        json_formatado = json.dumps(dados_finais, ensure_ascii=False, separators=(',', ':'),
                                    default=lambda o: float(o) if isinstance(o, Decimal) else str(o)
        )
    
        # logger.info(f"📦 [JSON DE RETORNO]: {json_formatado}")
        
        logger.info(f"🏁 [END] Processo concluído com sucesso para o Cliente: {payload.customer_id}")
        logger.info(f"=============================== [Finalizando Processo] ===============================")

        return {
            "status": "sucesso",
            "customer_id": payload.customer_id,
            "cemp": payload.cemp,
            "produtos_mapeados": resultado_grafo["final_results"]
        }
        
    except Exception as e:
        logger.info(f"ERRO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/processar-orcamento-arquivo")
async def processar_orcamento_arquivo(
    cemp: str = Form(..., description="ID da empresa"),
    customer_id: int = Form(..., description="ID do Cliente no banco"),
    file: UploadFile = File(..., description="Arquivo de pedido (Foto/Imagem, PDF, Excel ou Word)")
    ):
    try:
        logger.info(f"=============================== [Iniciando novo Processo] ===============================")
        logger.info(f"🚀 [START] Novo orçamento recebido (Empresa: {cemp} | Cliente: {customer_id}) | Arquivo: {file.filename}")

        # 1. O extrator identifica o formato (se for imagem, roda o OCR Vision da OpenAI)
        texto_extraido = await extrair_texto_de_arquivo(file)
        
        if not texto_extraido.strip():
            raise HTTPException(status_code=400, detail="Não foi possível extrair conteúdo legível deste arquivo.")
            
        # 2. Monta o payload de entrada mantendo o AgentState uniforme
        input_data = {
            "cemp": cemp,
            "customer_id": customer_id,
            "raw_request": texto_extraido
        }
        
        # 3. Dispara a esteira do LangGraph (Extração -> Histórico -> Contrato -> Catálogo -> Estoque)
        resultado_grafo = await agent_app.ainvoke(input_data)

        dados_finais = resultado_grafo.get("final_results", resultado_grafo)
        json_formatado = json.dumps(dados_finais, ensure_ascii=False, separators=(',', ':'), default=lambda o: float(o) if isinstance(o, Decimal) else str(o))
    
        # logger.info(f"📦 [JSON DE RETORNO]: {json_formatado}")
        
        logger.info(f"🏁 [END] Processo concluído com sucesso para o Cliente: {customer_id}")
        logger.info(f"=============================== [Finalizando Processo] ===============================")

        return {
            "status": "sucesso",
            "arquivo_processado": file.filename,
            "customer_id": customer_id,
            "cemp": cemp,
            "produtos_mapeados": resultado_grafo["final_results"]
        }
        
    except ValueError as ve:
        logger.info(f"ERRO: {str(e)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.info(f"ERRO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro crítico no processamento do arquivo: {str(e)}")
    
@router.get("/online")
def online():
    return {
        "status": "online"
    }