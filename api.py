import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
import sys

# Imports da sua aplicação
from app.database.database import init_db, close_db
from app.utils.logger import logger_api

# IMPORTANTE: Importe o router que criamos no arquivo anterior.
# Substitua 'app.api.routes' pelo caminho correto de onde você salvou o endpoint.
from app.api.routes import router as orcamento_router 

# 1. Gerencia o que acontece quando a API liga e desliga
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa ao iniciar a API (equivalente ao início do seu antigo main)
    logger_api.info("Iniciando conexão com o banco de dados...")
    await init_db()
    
    # Pausa aqui e deixa a API rodando e recebendo requisições
    yield
    
    # Executa ao desligar a API (Ctrl+C)
    logger_api.info("Fechando conexão com o banco de dados...")
    await close_db()

# 2. Instancia o FastAPI com o lifespan
app = FastAPI(
    title="API de Processamento de Orçamentos",
    lifespan=lifespan
)

# 3. Registra as suas rotas na API
app.include_router(orcamento_router)

# 4. Inicia o servidor localmente se rodar direto pelo Python
if __name__ == "__main__":
    logger_api.info("Iniciando servidor Uvicorn...")

    if getattr(sys, "frozen", False):
        # Executando como EXE
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False
        )
    else:
        # Executando pelo Python
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )