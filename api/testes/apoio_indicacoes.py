"""Funções de apoio dos testes de banco das indicações: criar o prestador com a primeira opinião
e opinar com SQL direto, como a API faz (spec das indicações, seção 4)."""

from sqlalchemy import text


def categoria_id(con, nome: str) -> int:
    return con.execute(
        text("select id from categoria_servico where nome = :n"), {"n": nome}
    ).scalar_one()


def criar_prestador(
    con,
    autor: int,
    *,
    telefone: str = "81999990001",
    nome: str = "Marcenaria Exemplo",
    categoria: str = "Móveis planejados",
    recomenda: bool = True,
    comentario: str | None = None,
) -> int:
    """O prestador e a primeira opinião, na transação de `con` (como o `POST` da API)."""
    prestador = con.execute(
        text(
            "insert into prestador (categoria_id, nome, nome_busca, telefone, criado_por)"
            " values (:c, :n, lower(:n), :t, :u) returning id"
        ),
        {"c": categoria_id(con, categoria), "n": nome, "t": telefone, "u": autor},
    ).scalar_one()
    opinar(con, prestador, autor, recomenda=recomenda, comentario=comentario)
    return prestador


def opinar(
    con, prestador: int, unidade: int, *, recomenda: bool = True, comentario: str | None = None
) -> None:
    con.execute(
        text(
            "insert into opiniao_servico (prestador_id, unidade_id, recomenda, comentario)"
            " values (:p, :u, :r, :c)"
        ),
        {"p": prestador, "u": unidade, "r": recomenda, "c": comentario},
    )
