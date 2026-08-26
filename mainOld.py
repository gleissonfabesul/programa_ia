import os
import sys
# Agora o Python sabe ler as pastas 'repositories' e 'schemas' perfeitamente
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database.database import init_db, close_db
from app.api.routes import router  # Certifique-se de que aponta para rotas/routes.py

# 🔥 BLINDAGEM DE CAMINHO: Injeta a raiz no Python antes de carregar o app
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(lifespan=lifespan)
app.include_router(router)