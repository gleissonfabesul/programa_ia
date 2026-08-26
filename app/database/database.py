from sqlalchemy import text
from app.utils.logger import logger
from app.database.banco import engine


async def init_db():

    try:

        with engine.connect() as conn:

            conn.execute(
                text("SELECT 1")
            )

        logger.info("Banco conectado com sucesso")

    except Exception as e:

        print(f"Erro banco: {e}")


async def close_db():

    engine.dispose()

    logger.info("Banco desconectado")