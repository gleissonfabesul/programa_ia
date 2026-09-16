from sqlalchemy import text
from datetime import datetime
from app.utils.logger import logger
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database.session import (
    SessaoLocal
)

class RepositorioProcessarOrcamentos:
    async def buscar_orcamentos_para_processar(self):
        query = text("""
                SELECT TOP 1 *
                FROM FABESUL_ERP_WEB.dbo.HABIL_ATIVIDADE_EXTRA WITH (UPDLOCK, READPAST)
                WHERE CD_SITUACAO = 173 AND DS_ATIVIDADE = 'Leitura Orçamento IA'
                ORDER BY CD_INDEX
        """)

        with SessaoLocal() as db:
            resultado = db.execute(query)
            return [

                dict(row._mapping)

                for row in resultado
            ]
        
    async def alterar_situacao_orcamento(self, codIndex: int, codSituacao: int):
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
    
        query = text("""
                UPDATE FABESUL_ERP_WEB.dbo.HABIL_ATIVIDADE_EXTRA SET
                CD_SITUACAO = :codSituacao, DT_ATUALIZACAO = :dtAtualizacao WHERE CD_INDEX = :codIndex
            """)

        with SessaoLocal() as db:
            db.execute(query, {"codIndex": codIndex, "codSituacao": codSituacao, "dtAtualizacao": agora.replace(tzinfo=None)})
            db.commit()
            
        return True
        
    async def adicionar_produtos_relacionados( self, produto, codChave):
        query = text("""
            INSERT INTO FABESUL_ERP_WEB.dbo.TEMP_REL_ORCAMENTO (
                CD_PRODUTO, DS_DESCRICAO, DS_MARCA, VL_PRODUTO, VL_TOTAL, VL_QTDE, 
                TX_UNIDADE, CD_ORCAMENTO, CD_CLIENTE, CD_NLAI,CD_GUID, TX_NOME, TX_FONE
            )
            VALUES (
                :CD_PRODUTO, :DS_DESCRICAO, :DS_MARCA, :VL_PRODUTO, :VL_TOTAL, :VL_QTDE,
                :TX_UNIDADE, :CD_ORCAMENTO, :CD_CLIENTE, :CD_NLAI, :CD_GUID, :TX_NOME, :TX_FONE
            )
            """)

        with SessaoLocal() as db:

            db.execute(query, {
                "CD_PRODUTO": produto["CD_PRODUTO"],
                "DS_DESCRICAO": produto["DS_DESCRICAO"],
                "DS_MARCA": produto["DS_MARCA"],
                "VL_PRODUTO": produto["VL_PRODUTO"],
                "VL_TOTAL": produto["VL_TOTAL"],
                "VL_QTDE": produto["VL_QTDE"],
                "TX_UNIDADE": produto["TX_UNIDADE"],
                "CD_ORCAMENTO": produto["CD_ORCAMENTO"],
                "CD_CLIENTE": produto["CD_CLIENTE"],
                "CD_NLAI": produto["CD_NLAI"],
                "CD_GUID": codChave,
                "TX_NOME": produto["TX_NOME"],
                "TX_FONE": produto["TX_FONE"]
            })

            db.commit()

            return True