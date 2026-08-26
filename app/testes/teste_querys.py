from app.repositories.repositorio_produtos import RepositorioProdutos
from app.repositories.repositorio_cliente import RepositorioCliente
import asyncio

repositorio = RepositorioProdutos()
repositorioCliente = RepositorioCliente()

async def buscapreco():
    cliente = await repositorioCliente.buscar_cliente(141560)
    print(cliente)

    if not cliente:
        print("Cliente não encontrado")
        return

    preco = await repositorio.buscar_preco_produto("01", 141560, cliente.cate, cliente.contri, 25561)
    print(f"\n")
    print(f"\n")
    print(f"\n")
    print(preco)


if __name__ == "__main__":
    asyncio.run(buscapreco())