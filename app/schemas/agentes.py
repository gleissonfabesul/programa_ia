from typing import List, Optional
from pydantic import BaseModel, Field

class MatchResult(BaseModel):
    original_query: str = Field(description="O nome exato do produto que foi enviado para busca")
    matched_id: Optional[str] = Field(description="O 'cpro' do produto no banco")
    matched_name: Optional[str] = Field(description="O 'descr' oficial no banco")
    found: bool

class MatchBatch(BaseModel):
    matches: List[MatchResult]

class ExtractedItem(BaseModel):
    product_name: str = Field(description="Nome completo do produto solicitado")
    quantidade: str = Field(description="Apenas o número da quantidade (ex: 8.00, 2.00, 15.00)")

class ExtractionBatch(BaseModel):
    items: List[ExtractedItem]