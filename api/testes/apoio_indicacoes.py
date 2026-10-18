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


# --- pela API (testes de rota) -------------------------------------------------------------------

NOVA = {
    "categoria_id": 1,  # Móveis planejados (o `banco_limpo` recarrega na ordem)
    "nome": "Marcenaria Exemplo",
    "telefone": "(81) 9 9999-0001",
    "recomenda": True,
    "comentario": "Fez a cozinha no prazo.",
}


def indicar(cliente, **campos) -> int:
    """Indica pela API e devolve o id (falha o teste se não for 201)."""
    resposta = cliente.post("/api/indicacoes", json={**NOVA, **campos})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def categoria_da_api(cliente, nome: str) -> int:
    itens = cliente.get("/api/indicacoes/categorias").json()["itens"]
    return next(c["id"] for c in itens if c["nome"] == nome)


def esconder_prestador_no_banco(engine, prestador: int, gestao: int) -> None:
    with engine.begin() as con:
        con.execute(
            text("update prestador set escondido_em = now(), escondido_por = :g where id = :p"),
            {"p": prestador, "g": gestao},
        )


def esconder_opiniao_no_banco(engine, prestador: int, unidade: int, gestao: int) -> None:
    with engine.begin() as con:
        con.execute(
            text(
                "update opiniao_servico set escondida_em = now(), escondida_por = :g"
                " where prestador_id = :p and unidade_id = :u"
            ),
            {"p": prestador, "u": unidade, "g": gestao},
        )


def opinar_no_banco(engine, prestador: int, unidade: int, *, recomenda=True, comentario=None):
    with engine.begin() as con:
        opinar(con, prestador, unidade, recomenda=recomenda, comentario=comentario)


def ids_da_lista(cliente, **filtros) -> list[int]:
    resposta = cliente.get("/api/indicacoes", params=filtros)
    assert resposta.status_code == 200, resposta.text
    return [i["id"] for i in resposta.json()["itens"]]
