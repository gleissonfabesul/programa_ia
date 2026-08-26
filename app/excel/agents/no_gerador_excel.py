import os
import uuid
import pandas as pd
from typing import Dict
from app.excel.estado_excel import DataProcessingState

def excel_generator_node(state: DataProcessingState) -> Dict:
    print("--- [BLOCO 5] GERANDO ARQUIVO EXCEL FINAL ---")
    dados_validados = state["execution_result"]
    
    df = pd.DataFrame(dados_validados)
    
    colunas_finais = ["codigo", "nome", "valor", "quantidade", "unidade_medida"]
    colunas_existentes = [col for col in colunas_finais if col in df.columns]
    df = df[colunas_existentes]
    
    # ➔ NOVO: Transforma quantidades iguais a 0 em campos vazios para o Excel
    if "quantidade" in df.columns:
        df["quantidade"] = df["quantidade"].apply(lambda x: "" if x == 0 or x == 0.0 else x)
    if "valor" in df.columns:
        df["valor"] = df["valor"].apply(lambda x: "" if x == 0 or x == 0.0 else x)
    
    PASTA_SAIDA = os.path.join(os.getcwd(), "saida")
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    nome_arquivo = f"relatorio_final_{uuid.uuid4().hex[:6]}.xlsx"
    caminho_saida = os.path.join(PASTA_SAIDA, nome_arquivo)
    
    df.to_excel(caminho_saida, index=False)
    print(f"✅ Excel salvo com sucesso com as colunas corretas em: {caminho_saida}")
    
    return {"final_excel_path": caminho_saida}