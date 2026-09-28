from sqlalchemy import text
from datetime import datetime
from app.utils.logger import logger
from datetime import datetime
from zoneinfo import ZoneInfo

from app.database.session import (
    SessaoLocal
)

class RepositorioProcessarOrcamentos:
    async def criar_atividade_importacao_api(
        self,
        cod_guid: str,
        customer_id: int,
        cemp: str,
        conteudo: bytes,
        cod_usuario: int
    ):
        query = text("""
            INSERT INTO FABESUL_ERP_WEB.dbo.HABIL_ATIVIDADE_EXTRA (
                DT_LANCAMENTO, DT_ATUALIZACAO, CD_USUARIO, NM_TABELA,
                DS_ATIVIDADE, CD_CHAVE, CD_SITUACAO, DS_FILTRO,
                IN_IMPOSTOS, IN_MARCA, TX_CONTEUDO, IN_CONTEUDO, TX_TEXTO
            )
            VALUES (
                :dt_lancamento, :dt_atualizacao, :cd_usuario, :nm_tabela,
                :ds_atividade, :cd_chave, :cd_situacao, :ds_filtro,
                :in_impostos, :in_marca, :tx_conteudo, :in_conteudo, :tx_texto
            )
        """)
        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        dados = {
            "dt_lancamento": agora,
            "dt_atualizacao": agora,
            "cd_usuario": cod_usuario,
            "nm_tabela": "TEMP_REL_ORCAMENTO",
            "ds_atividade": "Leitura Orçamento IA",
            "cd_chave": cod_guid,
            "cd_situacao": 173,
            "ds_filtro": "Orçamento Processado IA",
            "in_impostos": None,
            "in_marca": None,
            "tx_conteudo": conteudo,
            "in_conteudo": None,
            "tx_texto": __import__("json").dumps({
                "cemp": str(cemp),
                "ccli": customer_id,
                "outros": False,
                "PrecoMedio": False,
                "conteudo": "",
            }, ensure_ascii=False),
        }
        with SessaoLocal() as db:
            db.execute(query, dados)
            db.commit()
        return cod_guid

    async def buscar_orcamentos_para_processar(self):
        query = text("""
                SELECT TOP 1 *
                FROM FABESUL_ERP_WEB.dbo.HABIL_ATIVIDADE_EXTRA WITH (UPDLOCK, READPAST)
                WHERE CD_SITUACAO = 173
                    AND DS_ATIVIDADE = 'Leitura Orçamento IA'
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

    async def alterar_situacao_orcamento_por_chave(self, cod_guid: str, cod_situacao: int):
        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None)
        query = text("""
            UPDATE FABESUL_ERP_WEB.dbo.HABIL_ATIVIDADE_EXTRA
            SET CD_SITUACAO = :cod_situacao, DT_ATUALIZACAO = :dt_atualizacao
            WHERE CD_CHAVE = :cod_guid
        """)
        with SessaoLocal() as db:
            db.execute(query, {
                "cod_situacao": cod_situacao,
                "dt_atualizacao": agora,
                "cod_guid": cod_guid,
            })
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