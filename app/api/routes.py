from fastapi import APIRouter

from app.api.rotas.pedidos import (
    router as pedidos_router
)
from app.api.rotas.conversor import (
    router as arquivo_router
)
from app.api.rotas.importacao_orcamento import (
    router as importacao_orcamento_router
)

router = APIRouter()

router.include_router(pedidos_router)
router.include_router(arquivo_router)
router.include_router(importacao_orcamento_router)