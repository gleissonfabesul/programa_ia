import os
import sys
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv
from app.repositories.repositorio_produtos import RepositorioProdutos
from app.schemas.agentes import ExtractionBatch, MatchBatch
from app.schemas.agentes_excel import TabelaExcel

# Configuração dinâmica de caminhos para o Cache Vetorial
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)

EMBEDDING_DIR = os.path.join(BASE_DIR, "embedding")

os.makedirs(EMBEDDING_DIR, exist_ok=True)

ARQUIVO_VETORES_CACHE = os.path.join(EMBEDDING_DIR, "catalogo_vetores_cache.pkl")
ARQUIVO_CONTROLE_CACHE = os.path.join(EMBEDDING_DIR, "cache_vetores_data.txt")

# Instanciação dos Modelos de Linguagem
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
extraction_llm = llm.with_structured_output(ExtractionBatch)
mapper_llm = llm.with_structured_output(MatchBatch)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large")

# Extração para Excel
excel_llm = llm.with_structured_output(TabelaExcel)

# Instanciação do Repositório do Banco
repo = RepositorioProdutos()