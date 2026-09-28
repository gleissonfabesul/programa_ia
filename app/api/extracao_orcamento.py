from decimal import Decimal, InvalidOperation
from io import BytesIO
import magic
from typing import Any
import json
import zipfile

from app.configs.confgLang import excel_llm
from app.repositories.repositorio_cliente import RepositorioCliente
from app.repositories.repositorio_orcamento import RepositorioProcessarOrcamentos
from app.repositories.repositorio_produtos import RepositorioProdutos
from app.utils.extrator import extrair_texto_de_arquivo


def _codigo(valor: Any) -> int:
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    if not texto.isdigit():
        raise ValueError(f"Código de produto inválido: {valor}")
    return int(texto)


def _quantidade(valor: Any) -> Decimal:
    try:
        quantidade = Decimal(str(valor).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"Quantidade inválida: {valor}") from None

    if quantidade <= 0:
        raise ValueError(f"Quantidade deve ser maior que zero: {valor}")
    return quantidade


async def extrair_itens_por_codigo(conteudo: str) -> list[dict]:
    prompt = f"""
Você é um extrator de itens de pedidos de compra.

Sua única tarefa é identificar, no conteúdo recebido, pares:

CÓDIGO DO PRODUTO + QUANTIDADE SOLICITADA.

O arquivo pode ter qualquer formato de tabela, colunas em posições diferentes,
cabeçalhos diferentes ou não possuir cabeçalho.

REGRAS:

1. Identifique somente códigos de produtos e suas respectivas quantidades.
2. O código pode aparecer antes ou depois da descrição.
3. A quantidade pode estar em qualquer coluna.
4. Não dependa de nomes fixos de colunas.
5. Não confunda código com:
   - número da linha;
   - preço;
   - valor total;
   - telefone;
   - CNPJ;
   - CPF;
   - data;
   - número de pedido;
   - código de barras, quando não for o código do produto.
6. Preserve exatamente o código identificado.
7. Não invente códigos.
8. Não invente quantidades.
9. Se não houver certeza de que um número é código de produto, não retorne.
10. Se não houver certeza de que um número é quantidade, não retorne.
11. Não retorne descrição.
12. Não retorne preço.
13. Não retorne explicações.
14. Não retorne informações que não sejam código e quantidade.

RETORNE SOMENTE OS ITENS IDENTIFICADOS NO SCHEMA.

CONTEÚDO:
{conteudo}
"""
    resposta = await excel_llm.ainvoke(prompt)
    return [item.model_dump() for item in resposta.produtos]


async def salvar_itens_temp_rel_orcamento(
    itens: list[dict],
    cod_guid: str,
    customer_id: int,
    cemp: str
) -> list[dict]:
    cliente = await RepositorioCliente().buscar_cliente(customer_id)
    if not cliente:
        raise ValueError(f"Cliente não encontrado: {customer_id}")

    produtos_repo = RepositorioProdutos()
    orcamento_repo = RepositorioProcessarOrcamentos()
    agrupados: dict[int, Decimal] = {}

    for item in itens:
        codigo = _codigo(item.get("codigo"))
        quantidade = _quantidade(item.get("quantidade"))
        agrupados[codigo] = agrupados.get(codigo, Decimal("0")) + quantidade

    inseridos = []
    for numero_item, (codigo, quantidade) in enumerate(agrupados.items(), start=1):
        produto = await produtos_repo.buscar_produto_por_codigo(codigo)
        if not produto:
            raise ValueError(f"Produto não encontrado ou inativo: {codigo}")

        resultado_preco = await produtos_repo.buscar_preco_produto(cemp, cliente.ccli, cliente.cate, cliente.contri, codigo)
        
        if resultado_preco:
            preco = Decimal(str(resultado_preco[0]["PreCli"]))
        else:
            preco = Decimal("0")

        registro = {
            "CD_PRODUTO": codigo,
            "DS_DESCRICAO": produto.get("descr") or "",
            "DS_MARCA": "",
            "VL_PRODUTO": preco,
            "VL_TOTAL": preco * quantidade,
            "VL_QTDE": float(quantidade),
            "TX_UNIDADE": "",
            "CD_ORCAMENTO": 0,
            "CD_CLIENTE": customer_id,
            "CD_NLAI": numero_item,
            "TX_NOME": "",
            "TX_FONE": numero_item,
        }
        await orcamento_repo.adicionar_produtos_relacionados(registro, cod_guid)
        inseridos.append({
            "codigo": codigo,
            "descricao": registro["DS_DESCRICAO"],
            "preco": float(preco),
            "quantidade": float(quantidade),
        })

    return inseridos


async def processar_atividade_importacao_api(atividade: dict) -> bool:
    dados = json.loads(atividade["TX_TEXTO"])
    conteudo = atividade["TX_CONTEUDO"]

    if isinstance(conteudo, memoryview):
        conteudo = conteudo.tobytes()

    elif isinstance(conteudo, bytearray):
        conteudo = bytes(conteudo)

    if not conteudo:
        raise ValueError("Conteúdo do arquivo está vazio.")

    mime = magic.from_buffer(conteudo, mime=True)

    print(f"[DEBUG] Tipo Python: {type(conteudo)}")
    print(f"[DEBUG] Tamanho: {len(conteudo)} bytes")
    print(f"[DEBUG] Primeiros 32 bytes: {conteudo[:32]!r}")
    print(f"[DEBUG] MIME detectado: {mime}")

    extensao = "bin"

    if mime == "application/pdf":
        extensao = "pdf"

    elif mime.startswith("image/"):
        extensao = mime.split("/")[-1]

    elif mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        extensao = "xlsx"

    elif mime == "application/vnd.ms-excel":
        extensao = "xls"

    elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        extensao = "docx"

    elif mime == "application/zip":
        with zipfile.ZipFile(BytesIO(conteudo)) as zip_file:
            arquivos = zip_file.namelist()

            if any(nome.startswith("xl/") for nome in arquivos):
                extensao = "xlsx"

            elif any(nome.startswith("word/") for nome in arquivos):
                extensao = "docx"

    filename = f"arquivo.{extensao}"

    class FakeUploadFile:
        def __init__(
            self,
            filename: str,
            content: bytes,
            content_type: str = None
        ):
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

    arquivo = FakeUploadFile(
        filename=filename,
        content=conteudo,
        content_type=mime
    )

    texto = await extrair_texto_de_arquivo(arquivo)
    itens = await extrair_itens_por_codigo(texto)
    if not itens:
        raise ValueError("Nenhum código e quantidade foram identificados no arquivo.")

    await salvar_itens_temp_rel_orcamento(
        itens=itens,
        cod_guid=atividade["CD_CHAVE"],
        customer_id=int(dados["ccli"]),
        cemp=str(dados["cemp"]),
    )
    return True