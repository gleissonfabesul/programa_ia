from sqlalchemy import text
from datetime import datetime
from app.utils.logger import logger

from app.database.session import (
    SessaoLocal
)

class RepositorioCliente():
    async def buscar_cliente(self, ccli: int):
            query = text("""
                    SELECT TOP 1 *
                    FROM Fabesul.dbo.Cliente
                    WHERE ccli = :ccli 
                """)

            with SessaoLocal() as db:
                return db.execute(query, {"ccli": ccli}).mappings().first()