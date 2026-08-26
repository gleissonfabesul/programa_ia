from sqlalchemy import text
from datetime import datetime
from app.utils.logger import logger
import html

from app.database.session import (SessaoLocal)

class RepositorioEnviaEmail():
   async def enviar_email_erro_importacao(self, erro: str, cd_index: int):
        erro_html = html.escape(str(erro))
        corpo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset='UTF-8'/>
            <title>Fabesul - e-Mail</title>
        </head>
        <body bgcolor='FFFFFF'>
            <h3></h3>

            <table border='3'>
                <tr>
                    <th>Código</th>
                    <th>Data</th>
                    <th>Erro</th>
                </tr>

                <tr>
                    <td>{cd_index}</td>
                    <td>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</td>
                    <td>{erro_html}</td>
                </tr>
            </table>

        </body>
        </html>
        """

        query = text("""
            INSERT INTO Fabesul.dbo.ENVIO_EMAILS
            (
                TX_DESTINATARIOS,
                TXT_FROM,
                TXT_REPLAY,
                TX_ASSUNTO,
                TXT_CORPO,
                TX_ARQUIVOS,
                IN_STATUS
            )
            VALUES
            (
                :destinatarios,
                :remetente,
                :reply,
                :assunto,
                :corpo,
                :arquivos,
                :status
            )
        """)

        parametros = {
            "destinatarios": "sistemas@fabesul.com.br",
            "remetente": "2via@fabesul.com.br",
            "reply": "2via@fabesul.com.br",
            "assunto": "ERRO na Interpretação de orçamento IA",
            "corpo": corpo,
            "arquivos": "",
            "status": 0
        }

        with SessaoLocal() as db:
            db.execute(query, parametros)
            db.commit()