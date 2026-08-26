from pydantic import BaseModel, Field
from typing import List, Optional

class ProdutoExcel(BaseModel):
    nome: str = Field(description="A descrição completa do produto.")
    codigo: str = Field(description="O código real de identificação do produto (geralmente um número longo, ou pode estar como código, item). IGNORE números sequenciais de item (ex: 1, 2, 3, 40, 41).")
    quantidade: float = Field(description="A quantidade do produto. Se não encontrar nenhuma quantidade na linha, retorne 0.")
    unidade_medida: Optional[str] = Field(default="", description="A sigla da unidade de medida (ex: UN, CX, PE, GL). Se não encontrar, deixe vazio.")
    valor: Optional[float] = Field(description="O valor do produto. Se não encontrar nenhuma quantidade na linha, retorne 0.")

class TabelaExcel(BaseModel):
    produtos: List[ProdutoExcel]