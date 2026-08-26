import io
import base64
import pandas as pd
from pypdf import PdfReader
from docx import Document
from fastapi import UploadFile
from langchain_core.messages import HumanMessage
# Importa o seu LLM padrão configurado no seu arquivo confgLang
from app.configs.confgLang import llm 
from app.utils.logger import logger

async def extrair_texto_de_arquivo(file: UploadFile) -> str:
    logger.info(f"[AVISO] Iniciando leitura do arquivo {file.filename}")
    
    filename = file.filename.lower()
    conteudo_bytes = await file.read()
    
    # Reposiciona o ponteiro do arquivo para garantir leituras subsequentes se necessário
    await file.seek(0)
    
    logger.info(f"[ARQUIVO] Validando o tipo do arquivo...")

    # --- 📸 PROCESSAR IMAGENS (.png, .jpg, .jpeg) ---
    if filename.endswith(('.png', '.jpg', '.jpeg')):
        logger.info(f"[ARQUIVO] Imagem")
        
        logger.info(f"[OCR VISION] 👁️ Convertendo imagem {file.filename} para Base64 e acionando o modelo de visão...")
        
        # Transforma os bytes brutos da imagem em uma string Base64 legível por APIs visuais
        base64_image = base64.b64encode(conteudo_bytes).decode('utf-8')
        
        # Monta a estrutura de mensagem multimodal que a OpenAI exige para enxergar arquivos
        mensagem = HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text":"""
Você é um motor de OCR especializado em documentos de compras e tabelas.

OBJETIVO:
Extrair TODO o conteúdo visível da imagem sem resumir, sem interpretar e sem agrupar informações.

REGRAS OBRIGATÓRIAS:

1. Preserve TODAS as linhas da tabela.
2. Preserve TODAS as colunas existentes.
3. Não omita números.
4. Não omita quantidades.
5. Não reorganize os dados.
6. Não tente identificar produtos válidos.
7. Não tente corrigir nomes.
8. Não faça resumo.
9. Não explique nada.
10. Apenas transcreva.

IMPORTANTE:

Se existir uma tabela contendo:

Descrição | Quantidade

retorne obrigatoriamente no formato:

DESCRIÇÃO | QUANTIDADE

Exemplo:

CANETA AZUL | 10
PAPEL A4 | 40
CLIPS 8/0 | 10

Mesmo que a quantidade esteja distante da descrição na imagem,
você deve manter a associação correta entre descrição e quantidade.

Em alguns casos produtos terão nomes identicos, mas não são os mesmos produtos, um exemplo é quando é pilha AA e AAA,
caso apareça estes dados cuide para não inserir as quantidades erradas entre os produtos.

RETORNE SOMENTE O TEXTO EXTRAÍDO.
"""
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]
        )
        
        resposta = await llm.ainvoke([mensagem])

        return resposta.content

    # --- 📄 PROCESSAR PDF (.pdf) ---
    elif filename.endswith('.pdf'):
        logger.info(f"[ARQUIVO] PDF")

        pdf_stream = io.BytesIO(conteudo_bytes)
        reader = PdfReader(pdf_stream)
        texto_completo = []
        for page in reader.pages:
            texto_completo.append(page.extract_text() or "")

        logger.info("######### validando leutura do arquivo ######")
        logger.info(f"{texto_completo}")
        
        return "\n".join(texto_completo)
        
    # --- 📝 PROCESSAR WORD (.docx) ---
    elif filename.endswith('.docx'):
        logger.info(f"[ARQUIVO] Word")

        docx_stream = io.BytesIO(conteudo_bytes)
        doc = Document(docx_stream)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
    # --- 📊 PROCESSAR EXCEL (.xls, .xlsx) ---
    elif filename.endswith(('.xlsx', '.xls')):

        logger.info("[ARQUIVO] Excel (.xls, .xlsx)")

        excel_stream = io.BytesIO(conteudo_bytes)

        df = pd.read_excel(excel_stream, header=None)

        # remove linhas totalmente vazias
        df = df.dropna(how="all")

        # remove colunas totalmente vazias
        df = df.dropna(axis=1, how="all")

        # limpa NaN
        df = df.fillna("")

        linhas = []

        for _, row in df.iterrows():

            valores = []

            for v in row.tolist():

                texto = str(v).strip()

                if not texto:
                    continue

                # ignora lixo técnico
                if texto.lower().startswith("unnamed"):
                    continue

                if texto.lower() == "nan":
                    continue

                valores.append(texto)

            if valores:
                linhas.append(" | ".join(valores))

        texto_final = "\n".join(linhas)

        return texto_final
        
    else:
        raise ValueError("Formato de arquivo não suportado. Envie Imagens (PNG/JPG), PDF, XLSX ou DOCX.")