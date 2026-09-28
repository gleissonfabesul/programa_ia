from sqlalchemy import text

from app.database.session import (
    SessaoLocal
)

class RepositorioProdutos:
    async def buscar_produto_por_codigo(self, cpro: int):
        query = text("""
            SELECT TOP 1
                P.cpro,
                P.descr,
                P.precal
            FROM Fabesul.dbo.Produt P
            WHERE P.cpro = :cpro
        """)

        with SessaoLocal() as db:
            resultado = db.execute(query, {"cpro": cpro}).mappings().first()
            return dict(resultado) if resultado else None

    async def buscar_catalogo_produtos(self):

        query = text("""
        SELECT
                P.cpro,
                P.descr,
                P.precal,
                PD.disp,
                PD.cemp,
                ISNULL(SUM(NFI.qtdv), 0) AS qtde_vendida

            FROM Fabesul.dbo.Produt P

            INNER JOIN Fabesul.dbo.ProdutDisp PD
                ON PD.cpro = P.cpro

            LEFT JOIN Fabesul.dbo.NFItem NFI
                ON NFI.cpro = P.cpro

            LEFT JOIN Fabesul.dbo.MovSai MS
                ON MS.cemp = NFI.cemp
                AND MS.docf = NFI.nume
                AND NFI.seri = RIGHT(MS.seri, 2)

            WHERE
                PD.cemp IN ('01', '02', '04', '05') 
                and P.situ = 'Ativo'

                -- Data inicial
                AND MS.dtsa >= DATEADD(month, -3, GETDATE())
                AND MS.dtsa <= GETDATE()

            GROUP BY
                P.cpro,
                P.descr,
                P.precal,
                PD.disp,
                PD.cemp

            ORDER BY
                PD.cemp, P.descr
        """)

        with SessaoLocal() as db:

            resultado = db.execute(query)

            return [

                dict(row._mapping)

                for row in resultado
            ]

    async def buscar_produtos_contrato(self, cliente_id: int, cemp: str):
        query = text("""
        Select Top 450
            C.cpro,
            C.card, 
            C.prect,
            P.descr,
            PD.disp
        from Fabesul.dbo.ClienPr C
        Inner join Fabesul.dbo.Produt as P ON P.cpro = C.cpro
        inner join Fabesul.dbo.ProdutDisp as PD ON PD.cpro = P.cpro
            where C.ccli = :cliente_id and PD.cemp = :cemp
        """)

        with SessaoLocal() as db:

            resultado = db.execute(

                query,

                {
                    "cliente_id": cliente_id,
                    "cemp": cemp
                }
            )

            return [

                dict(row._mapping)

                for row in resultado
            ]

    async def buscar_historico_produtos(self, cliente_id: int, cemp: str):
        query = text("""
        Select Top 300
            OI.nume, 
            OI.cpro, 
            OI.descr, 
            OI.prec, 
            OI.qtde, 
            OI.vtot,
            PD.disp
        from Fabesul.dbo.Orcamento O
        Inner join Fabesul.dbo.OrcItem as OI ON OI.nume = O.nume
        inner join Fabesul.dbo.ProdutDisp as PD ON OI.cpro = PD.cpro
        where O.hora >= DATEADD(month, -3, GETDATE()) AND O.hora <= GETDATE()
        AND O.ccli = :cliente_id AND PD.cemp = :cemp 
        order by OI.nume DESC
        """)

        with SessaoLocal() as db:

            resultado = db.execute(

                query,

                {
                    "cliente_id": cliente_id,
                    "cemp": cemp
                }
            )

            return [

                dict(row._mapping)

                for row in resultado
            ]
        
    async def buscar_produto_disp(self, cpro: int, cemp: str):
        query = text("""
            SELECT TOP 5 P.cpro, P.descr, P.precal, PD.disp
            FROM Fabesul.dbo.Produt P
            INNER JOIN Fabesul.dbo.ProdutDisp as PD ON PD.cpro = P.cpro
            WHERE PD.cpro = :cpro 
            AND PD.disp > 0 
            AND P.situ = 'Ativo' 
            AND PD.cemp = :cemp
        """)
    
        with SessaoLocal() as db:
            # 🌟 CORREÇÃO: Todos os parâmetros passados juntos em um único dicionário
            resultado = db.execute(query, {"cpro": cpro, "cemp": str(cemp).strip()})
            return [dict(row._mapping) for row in resultado]

    async def buscar_similares_com_estoque(self, descricao_original: str, cemp: str):
        if(cemp == "01"):
            query = text("""
                SELECT TOP 200 
                P.cpro, P.descr, P.precal, PD.disp
                FROM Fabesul.dbo.Produt P
                INNER JOIN Fabesul.dbo.ProdutDisp as PD ON PD.cpro = P.cpro
                WHERE P.descr LIKE :busca 
                AND PD.disp > 0 
                AND P.situ = 'Ativo' 
                AND PD.cemp IN (:cemp, '05') order by P.descr
            """)
        else:
            query = text("""
                SELECT TOP 200 
                P.cpro, P.descr, P.precal, PD.disp
                FROM Fabesul.dbo.Produt P
                INNER JOIN Fabesul.dbo.ProdutDisp as PD ON PD.cpro = P.cpro
                WHERE P.descr LIKE :busca 
                AND PD.disp > 0 
                AND P.situ = 'Ativo' 
                AND PD.cemp = :cemp order by P.descr
            """)
        

        # Tratamento da string para buscar a primeira palavra
        primeira_palavra = descricao_original.split()[0] + "%"
        
        with SessaoLocal() as db:
            # 🌟 CORREÇÃO: Parâmetros unificados num dicionário só
            resultado = db.execute(query, {"busca": primeira_palavra, "cemp": str(cemp).strip()})
            return [dict(row._mapping) for row in resultado]
        
    async def buscar_produto_contrato(self, cliente_id: int, cpro: str):
        query = text("""
            SELECT prect
            FROM Fabesul.dbo.ClienPr
            WHERE ccli = :cliente_id
            AND cpro = :cpro
        """)

        with SessaoLocal() as db:
            return db.execute(query, { "cliente_id": cliente_id, "cpro": cpro }).scalar()
        
    async def buscar_preco_produto(self, cemp: str, ccli: int, categoria: str, contribuinte: str, cpro: int):
        cemp_format = cemp
        
        if not cemp.startswith("0"):
            cemp_format = "0" + cemp

        where_clause = f"""
            Where produt.cpro = {cpro}
            and produtdisp.cemp = {cemp_format}
            and produtdisp.disp > 0
            and produt.IN_VDA_CTRL_UNIDADE = 0
            and produt.cpro not in (
                select cpro from clienprproibido where ccli = {ccli}
            )
        """

        # Executamos a procedure diretamente, sem tabela temporária (#TmpAtuConProduto01)
        sql = f"""
            EXEC Fabesul.dbo.SP_ConProdutoMCM18062026
                    '{where_clause}',
                    'CONPRODU',
                    '{cemp_format}',
                    {ccli},
                    '{contribuinte}',
                    '{categoria}',
                    'N',
                    'N',
                    '',
                    'Parte da Descrição';
        """
        
        with SessaoLocal() as db:
            resultado = db.execute(text(sql))

            return [dict(row._mapping)for row in resultado]

    async def buscar_precos_produtos(self, cemp: str, ccli: int, categoria: str, contribuinte: str, lista_cpros: list[int]):
        cpros_formatados = ", ".join(str(cpro) for cpro in lista_cpros)

        cemp_format = cemp
        
        if not cemp.startswith("0"):
            cemp_format = "0" + cemp

        where_clause = f"""
            Where produt.cpro IN ({cpros_formatados})
            and produtdisp.cemp = {cemp_format}
            and produtdisp.disp > 0
            and produt.IN_VDA_CTRL_UNIDADE = 0
            and produt.cpro not in (
                select cpro from clienprproibido where ccli = {ccli}
            )
        """

        sql = f"""
            EXEC Fabesul.dbo.SP_ConProdutoMCM18062026
                    '{where_clause}',
                    'CONPRODU',
                    '{cemp_format}',
                    {ccli},
                    '{contribuinte}',
                    '{categoria}',
                    'N',
                    'N',
                    '',
                    'Parte da Descrição';
        """

        with SessaoLocal() as db:

            conn = db.connection()
            cursor = conn.connection.cursor()

            cursor.execute(sql)

            while True:

                if cursor.description:

                    colunas = [c[0] for c in cursor.description]

                    if "Retorno" not in colunas:

                        linhas = cursor.fetchall()

                        return [
                            dict(zip(colunas, linha))
                            for linha in linhas
                        ]

                    else:
                        # descarta esse result set
                        cursor.fetchall()

                if not cursor.nextset():
                    break

            return []

    async def buscar_preco_medio(self, cpro: int, cemp: str):
        query = text("""
            SELECT 
                CAST(AVG(X.prec) AS DECIMAL(18,2)) AS PreCli
            FROM
            (
                SELECT TOP 400
                    I.prec
                FROM Fabesul.dbo.NFItem I WITH (NOLOCK)
                INNER JOIN Fabesul.dbo.NFiscal N WITH (NOLOCK)
                    ON N.cemp = I.cemp
                AND N.seri = I.seri
                AND N.nume = I.nume
                WHERE I.cemp = :cemp
                AND I.cpro = :cpro
                AND I.prec > 0
                AND N.situ = 'I'
                ORDER BY N.dtnf DESC
            ) X
            OPTION (RECOMPILE);
            """)

        with SessaoLocal() as db:
            resultado = db.execute(
                query,
                {"cpro": cpro, "cemp": cemp}
            ).fetchone()

            if resultado and resultado.PreCli is not None:
                return resultado.PreCli

            return None