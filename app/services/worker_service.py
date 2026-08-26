import asyncio
import json
import magic
from decimal import Decimal
from io import BytesIO
from app.orcamento.fluxo_orcamento import app as agent_app
from app.utils.logger import logger
from app.utils.extrator import extrair_texto_de_arquivo
from app.repositories.repositorio_orcamento import RepositorioProcessarOrcamentos
from app.repositories.repositorio_produtos import RepositorioProdutos
from app.repositories.repositorio_cliente import RepositorioCliente
from app.repositories.repositorio_envia_email import RepositorioEnviaEmail


async def executar_worker():
    repositorio = RepositorioProcessarOrcamentos() 
    repositorio_email = RepositorioEnviaEmail()
    logger.info("=============================== [Buscando Orçamentos] ===============================")
    cont = 0
    while True:
        await asyncio.sleep(2)
        try:
            habil_atividades = await repositorio.buscar_orcamentos_para_processar()

            if not habil_atividades:
                cont += 1

                if(cont > 10):
                    logger.info(f"[Processo] Nenhum orçamento encontrado.")
                    logger.info("[Processo] Entrando em espera por 4 minutos...")
                    await asyncio.sleep(240)
                    logger.info("=============================== [Buscando Orçamentos] ===============================")
                    cont = 0  

                await asyncio.sleep(1)
                continue
            
            habil_atividade = habil_atividades[0]

            dados_texto = json.loads(habil_atividade["TX_TEXTO"])

            try:
                resultado = await processar_orcamento(habil_atividade)

                itens_processados = await processar_itens_orcamento(habil_atividade["CD_CHAVE"], resultado, dados_texto.get("ccli"), dados_texto.get("cemp"))

                if(itens_processados):
                    await repositorio.alterar_situacao_orcamento(habil_atividade["CD_INDEX"], 172)

            except Exception as ex:
                logger.error(f"❌ ERRO AO PROCESSAR ORÇAMENTO" f" {habil_atividade["CD_INDEX"]}: {str(ex)}")
                await repositorio_email.enviar_email_erro_importacao(erro=str(ex), cd_index=habil_atividade["CD_INDEX"])
                await repositorio.alterar_situacao_orcamento(habil_atividade["CD_INDEX"], 486)

        except Exception as ex:
            logger.error(f"❌ ERRO CRÍTICO NO WORKER: {str(ex)}")

            await asyncio.sleep(5)


async def processar_orcamento(habil_atividade):
    dados_texto = json.loads(habil_atividade["TX_TEXTO"])

    logger.info(f"=============================== [Iniciando Processo] ===============================")
    
    logger.info(f"🚀 [START] Novo orçamento recebido " f"(Empresa: 0{dados_texto.get("cemp")} | Cliente: {dados_texto.get("ccli")})")

    texto_extraido = ""
    texto_ocr = ""

    conteudo = dados_texto.get("conteudo")

    if conteudo and conteudo.strip():
        logger.info("📝 [MODO TEXTO] Processando conteúdo textual enviado")

        texto_extraido = conteudo.strip()

    # ARQUIVO
    if habil_atividade["TX_CONTEUDO"]:
        logger.info("📎 [MODO ARQUIVO] Processando arquivo")

        conteudo_binario = habil_atividade["TX_CONTEUDO"]

        if isinstance(conteudo_binario, memoryview):
            conteudo_binario = conteudo_binario.tobytes()

        elif isinstance(conteudo_binario, bytearray):
            conteudo_binario = bytes(conteudo_binario)

        mime = magic.from_buffer(conteudo_binario, mime=True)

        extensao = "bin"

        if mime == "application/pdf":
            extensao = "pdf"

        elif mime.startswith("image/"):
            extensao = mime.split("/")[-1]

        elif mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            extensao = "xlsx"

        elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extensao = "docx"

        filename = f"arquivo.{extensao}"

        class FakeUploadFile:
            def __init__(self, filename: str, content: bytes, content_type: str = None):
                self.filename = filename
                self.content_type = content_type
                self._file = BytesIO(content)

            async def read(self):
                self._file.seek(0)
                return self._file.read()

            async def seek(self, offset: int):
                self._file.seek(offset)

            async def close(self):
                self._file.close()

        fake_file = FakeUploadFile(
            filename=filename,
            content=conteudo_binario,
            content_type=mime
        )

        logger.info("🔍 [OCR] Extraindo conteúdo do arquivo")

        texto_ocr = await extrair_texto_de_arquivo(fake_file)

        # logger.info("========== OCR EXTRAÍDO ==========")
        # logger.info(texto_ocr)
        # logger.info("==================================")

        logger.info("✅ [OCR] Conteúdo extraído com sucesso")

    if not texto_extraido.strip() and not texto_ocr.strip():
        raise Exception("Orçamento sem conteúdo textual ou arquivo.")

    cemp = dados_texto.get("cemp")
    ccli = dados_texto.get("ccli")

    input_data = {
        "cemp": "0" + str(cemp),
        "customer_id": ccli,
        "raw_request": f"""
                === TEXTO DIGITADO ===
                {texto_extraido}

                === ARQUIVO EXTRAÍDO ===
                {texto_ocr}
                """
    }

    logger.info("========== CONTEÚDO ENVIADO AO AGENTE ==========")
    logger.info(input_data["raw_request"])
    logger.info("================================================")

    resultado_grafo = await agent_app.ainvoke(input_data)

    dados_finais = resultado_grafo.get("final_results", resultado_grafo)

    # json_formatado = json.dumps(dados_finais, ensure_ascii=False, separators=(',', ':'),
    #     default=lambda o: float(o) if isinstance(o, Decimal) else str(o))
    
    # logger.info(f"📦 [JSON DE RETORNO]: {json_formatado}")

    logger.info(f"=============================== [Processo Finalizado] ===============================")

    return dados_finais

async def processar_itens_orcamento(codGUID: str, itens: list, ccli: int, cemp: str):
    repositorio = RepositorioProcessarOrcamentos()
    repositorio_produto = RepositorioProdutos()
    repositorio_cliente = RepositorioCliente()

    cliente = await repositorio_cliente.buscar_cliente(ccli)

    itens_agrupados = []

    for item in itens:
        id_produto = str(item.get("id", "")).strip().upper()

        encontrado = False

        for item_existente in itens_agrupados:

            id_existente = str(
                item_existente.get("id", "")
            ).strip().upper()

            if id_produto == id_existente:

                quantidade_atual = Decimal(
                    str(item_existente.get("quantidade", 0))
                )

                quantidade_nova = Decimal(
                    str(item.get("quantidade", 0))
                )

                item_existente["quantidade"] = float(
                    quantidade_atual + quantidade_nova
                )

                encontrado = True
                break

        if not encontrado:
            itens_agrupados.append(item.copy())

    cont = 0
    for item in itens_agrupados:
        id_produto = str(item.get("id", "")).strip().upper()

        preco = 0
        valorTotal = 0
        if id_produto == "N/A":
            preco = Decimal("0.00")
            valorTotal = Decimal("0.00")
        elif item.get("source") == "contrato":
            preco = await repositorio_produto.buscar_produto_contrato(ccli, item.get("id"))
            if preco is not None:
                quantidade = Decimal(str(item.get("quantidade", 0)))
                valorTotal = preco * quantidade
            else:
                preco = Decimal("0.00")
        else:
            resultado_preco = await repositorio_produto.buscar_preco_produto(cemp, cliente.ccli, cliente.cate, cliente.contri, item.get("id"))

            if resultado_preco:
                preco = Decimal(str(resultado_preco[0].get("PreCli", 0)))
                quantidade = Decimal(str(item.get("quantidade", 0)))
                valorTotal = preco * quantidade
            else:
                preco = Decimal("0.00")
                valorTotal = Decimal("0.00")

        cont += 1
        produto = {
            "CD_PRODUTO": 0 if item.get("id") == "N/A" else item.get("id"),
            "DS_DESCRICAO": item.get("descr") or "",
            "DS_MARCA": item.get("source") or "",
            "VL_PRODUTO": preco,
            "VL_TOTAL": 0 if valorTotal == 0 else valorTotal,
            "VL_QTDE": float(item.get("quantidade", 0)),
            "TX_UNIDADE": "",
            "CD_ORCAMENTO": 0,
            "CD_CLIENTE": ccli,
            "CD_NLAI": cont,
            "TX_NOME": item.get("status_estoque")
        }

        await repositorio.adicionar_produtos_relacionados( produto, codGUID )

    return True