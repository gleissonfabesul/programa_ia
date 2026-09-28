from uuid import uuid4
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.extracao_orcamento import processar_atividade_importacao_api
from app.repositories.repositorio_orcamento import RepositorioProcessarOrcamentos
from app.utils.logger import logger_api

router = APIRouter(prefix="/api", tags=["Importação de orçamento"])


@router.post("/importar-orcamento-arquivo")
async def importar_orcamento_arquivo(
    cemp: str = Form(..., description="Código da empresa"),
    customer_id: int = Form(..., description="Código do cliente"),
    file: UploadFile = File(..., description="TXT, imagem, PDF ou Excel com códigos e quantidades"),
    codigo_user: int = Form(..., description="Código do usuário"),
):
    cod_guid = None
    try:
        logger_api.info(
            f"[API IMPORTAÇÃO] Arquivo {file.filename} recebido para o cliente {customer_id}")
        
        conteudo = await file.read()
        
        if not conteudo:
            raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")

        if not cemp:
                    raise HTTPException(status_code=400, detail="Empresa não informada.")

        if not customer_id:
                    raise HTTPException(status_code=400, detail="Cliente não informado.")
        
        if not codigo_user:
                    raise HTTPException(status_code=400, detail="Usuário não informado.")

        cod_guid = await RepositorioProcessarOrcamentos().criar_atividade_importacao_api(
            cod_guid=str(uuid4()),
            customer_id=customer_id,
            cemp=cemp,
            conteudo=conteudo,
            cod_usuario=codigo_user
        )
        atividade = {
            "CD_CHAVE": cod_guid,
            "TX_CONTEUDO": conteudo,
            "TX_TEXTO": json.dumps({
                "cemp": str(cemp),
                "ccli": customer_id,
            }, ensure_ascii=False),
        }
        await processar_atividade_importacao_api(atividade)
        await RepositorioProcessarOrcamentos().alterar_situacao_orcamento_por_chave(
            cod_guid=cod_guid,
            cod_situacao=172,
        )

        return {
            "status": "sucesso",
            "atividade": "Leitura Orçamento API",
            "codGUID": cod_guid,
            "arquivo_processado": file.filename,
            "customer_id": customer_id,
            "cemp": cemp,
            "situacao": 172,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        if cod_guid:
            await RepositorioProcessarOrcamentos().alterar_situacao_orcamento_por_chave(
                cod_guid=cod_guid,
                cod_situacao=486,
            )
        logger_api.error(f"[API IMPORTAÇÃO] Dados inválidos: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if cod_guid:
            await RepositorioProcessarOrcamentos().alterar_situacao_orcamento_por_chave(
                cod_guid=cod_guid,
                cod_situacao=486,
            )
        logger_api.error(f"[API IMPORTAÇÃO] Erro ao importar arquivo: {exc}")
        raise HTTPException(status_code=500, detail="Erro ao importar o arquivo.") from exc