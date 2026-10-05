"""Regras dos avisos que o próprio banco garante (migração 0002; modelo, seção 4; RN-05).

Tudo como o usuário `app`, do jeito que a API conecta em produção.
"""

from datetime import UTC, datetime

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    with engine_app.begin() as con:
        b1 = criar_bloco(con, 1)
        b2 = criar_bloco(con, 2)
        u = criar_unidade(con, b2, "304")
    return {"b1": b1, "b2": b2, "u": u}


def _aviso(con, u: int, *, para_todos=True, fixado=False) -> int:
    return con.execute(
        text(
            "insert into aviso (publicado_por, publicado_como, para_todos, fixado)"
            " values (:u, 'comissao', :t, :f) returning id"
        ),
        {"u": u, "t": para_todos, "f": fixado},
    ).scalar_one()


def _versao(con, aviso: int, u: int, versao: int = 1, titulo="Título", texto="Texto") -> None:
    con.execute(
        text(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " values (:a, :v, :t, :x, :u)"
        ),
        {"a": aviso, "v": versao, "t": titulo, "x": texto, "u": u},
    )


@pytest.fixture
def aviso(engine_app, ids) -> int:
    with engine_app.begin() as con:
        a = _aviso(con, ids["u"])
        _versao(con, a, ids["u"])
    return a


def _negado(engine, comando: str, **parametros) -> None:
    with pytest.raises(ProgrammingError) as erro, engine.begin() as con:
        con.execute(text(comando), parametros)
    assert isinstance(erro.value.orig, InsufficientPrivilege)


# --- nada oficial é apagado nem reescrito -----------------------------------------------------


@pytest.mark.parametrize("tabela", ["aviso", "aviso_versao", "aviso_bloco", "aviso_leitura"])
def test_app_nao_apaga_aviso(engine_app, aviso, tabela):
    _negado(engine_app, f"delete from {tabela}")


@pytest.mark.parametrize(
    "comando",
    [
        "update aviso_versao set texto = 'adulterado'",
        "update aviso_bloco set bloco_id = bloco_id",
        "update aviso_leitura set lido_em = now()",
        "update aviso set para_todos = false",
        "update aviso set publicado_por = publicado_por",
        "update aviso set publicado_em = now()",
        "update aviso set publicado_como = 'admin'",
    ],
)
def test_app_nao_reescreve_o_que_foi_publicado(engine_app, aviso, comando):
    _negado(engine_app, comando)


def test_app_fixa_e_arquiva(engine_app, aviso):
    with engine_app.begin() as con:
        con.execute(text("update aviso set fixado = true where id = :a"), {"a": aviso})
        arquivado = con.execute(
            text(
                "update aviso set arquivado_em = '2001-01-01 00:00+00' where id = :a"
                " returning arquivado_em"
            ),
            {"a": aviso},
        ).scalar_one()
    # A data é a do banco, não a mandada pelo app.
    assert arquivado.year != 2001


def test_arquivado_nao_volta_ao_mural_pelo_banco(engine_app, aviso):
    with engine_app.begin() as con:
        con.execute(text("update aviso set arquivado_em = now() where id = :a"), {"a": aviso})
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        con.execute(text("update aviso set arquivado_em = null where id = :a"), {"a": aviso})


def test_arquivar_de_novo_nao_muda_a_data(engine_app, aviso):
    with engine_app.begin() as con:
        primeira = con.execute(
            text("update aviso set arquivado_em = now() where id = :a returning arquivado_em"),
            {"a": aviso},
        ).scalar_one()
    with engine_app.begin() as con:
        segunda = con.execute(
            text("update aviso set arquivado_em = now() where id = :a returning arquivado_em"),
            {"a": aviso},
        ).scalar_one()
    assert segunda == primeira


# --- datas carimbadas pelo banco --------------------------------------------------------------


def test_datas_do_aviso_sao_do_banco(engine_app, ids):
    antes = datetime.now(UTC)
    with engine_app.begin() as con:
        a = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos, publicado_em)"
                " values (:u, 'comissao', true, '2001-01-01 00:00+00') returning id"
            ),
            {"u": ids["u"]},
        ).scalar_one()
        con.execute(
            text(
                "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por, criada_em)"
                " values (:a, 1, 't', 'x', :u, '2001-01-01 00:00+00')"
            ),
            {"a": a, "u": ids["u"]},
        )
        con.execute(
            text(
                "insert into aviso_leitura (aviso_id, unidade_id, lido_em)"
                " values (:a, :u, '2001-01-01 00:00+00')"
            ),
            {"a": a, "u": ids["u"]},
        )
        datas = con.execute(
            text(
                "select a.publicado_em, v.criada_em, l.lido_em from aviso a"
                " join aviso_versao v on v.aviso_id = a.id"
                " join aviso_leitura l on l.aviso_id = a.id where a.id = :a"
            ),
            {"a": a},
        ).one()
    for data in datas:
        assert abs((data - antes).total_seconds()) < 60


# --- versões em sequência ---------------------------------------------------------------------


def test_versao_seguinte_aceita(engine_app, aviso, ids):
    with engine_app.begin() as con:
        _versao(con, aviso, ids["u"], versao=2, texto="Corrigido")
        maior = con.execute(
            text("select max(versao) from aviso_versao where aviso_id = :a"), {"a": aviso}
        ).scalar_one()
    assert maior == 2


@pytest.mark.parametrize("versao", [0, 1, 3])
def test_versao_fora_de_sequencia_recusada(engine_app, aviso, ids, versao):
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        _versao(con, aviso, ids["u"], versao=versao)


@pytest.mark.parametrize(
    ("titulo", "texto"),
    [("", "x"), ("   ", "x"), ("t" * 121, "x"), ("t", ""), ("t", "x" * 10_001)],
)
def test_titulo_e_texto_com_limites(engine_app, ids, titulo, texto):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        a = _aviso(con, ids["u"])
        _versao(con, a, ids["u"], titulo=titulo, texto=texto)


# --- aviso completo no commit -----------------------------------------------------------------


def test_aviso_sem_versao_recusado_no_commit(engine_app, ids):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _aviso(con, ids["u"])
    assert restricao(erro.value) == "aviso_completo"


def test_aviso_de_blocos_sem_bloco_recusado(engine_app, ids):
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        a = _aviso(con, ids["u"], para_todos=False)
        _versao(con, a, ids["u"])
    assert restricao(erro.value) == "aviso_completo"


def test_aviso_de_blocos_com_bloco_aceito(engine_app, ids):
    with engine_app.begin() as con:
        a = _aviso(con, ids["u"], para_todos=False)
        _versao(con, a, ids["u"])
        con.execute(
            text("insert into aviso_bloco (aviso_id, bloco_id) values (:a, :b)"),
            {"a": a, "b": ids["b1"]},
        )


def test_bloco_em_aviso_para_todos_recusado(engine_app, aviso, ids):
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        con.execute(
            text("insert into aviso_bloco (aviso_id, bloco_id) values (:a, :b)"),
            {"a": aviso, "b": ids["b1"]},
        )


def test_leitura_conta_uma_vez(engine_app, aviso, ids):
    inserir = text(
        "insert into aviso_leitura (aviso_id, unidade_id) values (:a, :u) on conflict do nothing"
    )
    with engine_app.begin() as con:
        con.execute(inserir, {"a": aviso, "u": ids["u"]})
        con.execute(inserir, {"a": aviso, "u": ids["u"]})
        total = con.execute(text("select count(*) from aviso_leitura")).scalar_one()
    assert total == 1
