import asyncio
import json
from decimal import Decimal

from app.database.database import init_db, close_db
from app.services.worker_service import executar_worker
from app.utils.logger import logger

async def main():
    await init_db()

    try:
        await executar_worker()

    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())