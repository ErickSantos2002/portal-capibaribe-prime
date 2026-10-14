"""Funções de apoio dos testes de banco das enquetes (M4): criar a enquete inteira e votar com
SQL direto, como os épicos fazem (spec do M4, seção 2). As fixtures `ids`, `aberta` e `votada`
ficam no `conftest.py`."""

from sqlalchemy import Engine, text


def aviso_da_enquete(con, unidade: int, blocos: tuple[int, ...] = ()) -> int:
    """O aviso automático, com o mesmo destino da enquete (o banco confere no commit)."""
    a = con.execute(
        text(
            "insert into aviso (publicado_por, publicado_como, para_todos)"
            " values (:u, 'comissao', :todos) returning id"
        ),
        {"u": unidade, "todos": not blocos},
    ).scalar_one()
    for bloco in blocos:
        con.execute(
            text("insert into aviso_bloco (aviso_id, bloco_id) values (:a, :b)"),
            {"a": a, "b": bloco},
        )
    con.execute(
        text(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " values (:a, 1, 'Enquete nova', 'Vote', :u)"
        ),
        {"a": a, "u": unidade},
    )
    return a


def criar_enquete(
    con,
    autor: int,
    *,
    opcoes: tuple[str, ...] = ("Terça à noite", "Quinta à noite", "Sábado de manhã"),
    blocos: tuple[int, ...] = (),
    multipla: bool = False,
    encerra: str = "now() + interval '7 days'",
    pergunta: str = "Qual o melhor dia para a reunião?",
    para_todos: bool | None = None,
    aviso_blocos: tuple[int, ...] | None = None,
) -> int:
    """Cria a enquete inteira na transação de `con` (aviso, enquete, opções, blocos)."""
    enquete = con.execute(
        text(
            "insert into enquete (pergunta, multipla_escolha, mostrar_resultado, encerra_em,"
            f" para_todos, criada_por, aviso_id) values (:p, :m, 'durante', {encerra},"
            " :todos, :u, :a) returning id"
        ),
        {
            "p": pergunta,
            "m": multipla,
            "todos": (not blocos) if para_todos is None else para_todos,
            "u": autor,
            "a": aviso_da_enquete(con, autor, aviso_blocos if aviso_blocos is not None else blocos),
        },
    ).scalar_one()
    for ordem, texto in enumerate(opcoes, start=1):
        con.execute(
            text("insert into enquete_opcao (enquete_id, texto, ordem) values (:e, :t, :o)"),
            {"e": enquete, "t": texto, "o": ordem},
        )
    for bloco in blocos:
        con.execute(
            text("insert into enquete_bloco (enquete_id, bloco_id) values (:e, :b)"),
            {"e": enquete, "b": bloco},
        )
    return enquete


def opcoes_da_enquete(con, enquete: int) -> list[int]:
    return list(
        con.execute(
            text("select id from enquete_opcao where enquete_id = :e order by ordem"),
            {"e": enquete},
        ).scalars()
    )


def votar(con, enquete: int, unidade: int, *opcoes: int) -> None:
    """A gravação do voto como o épico B faz (spec, seção 2.6)."""
    con.execute(
        text(
            "insert into voto (enquete_id, unidade_id) values (:e, :u)"
            " on conflict (enquete_id, unidade_id) do update set votado_em = excluded.votado_em"
        ),
        {"e": enquete, "u": unidade},
    )
    con.execute(
        text("delete from voto_opcao where enquete_id = :e and unidade_id = :u"),
        {"e": enquete, "u": unidade},
    )
    for opcao in opcoes:
        con.execute(
            text("insert into voto_opcao (enquete_id, unidade_id, opcao_id) values (:e, :u, :o)"),
            {"e": enquete, "u": unidade, "o": opcao},
        )


def votos_da_enquete(engine: Engine, enquete: int) -> list[tuple[int, list[int]]]:
    with engine.connect() as con:
        return [
            (u, list(o))
            for u, o in con.execute(
                text(
                    "select v.unidade_id, array_agg(o.opcao_id order by o.opcao_id)"
                    " from voto v join voto_opcao o using (enquete_id, unidade_id)"
                    " where v.enquete_id = :e group by v.unidade_id order by v.unidade_id"
                ),
                {"e": enquete},
            )
        ]
