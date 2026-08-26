from fastapi import APIRouter

from app.api.rotas.pedidos import (
    router as pedidos_router
)
from app.api.rotas.conversor import (
    router as arquivo_router
)

router = APIRouter()

router.include_router(pedidos_router)
router.include_router(arquivo_router)