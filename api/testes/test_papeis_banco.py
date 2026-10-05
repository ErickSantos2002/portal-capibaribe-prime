"""Papéis e contatos da unidade: regras que a migração 0002 pôs no banco (H-09, RF-04)."""

import threading
from datetime import UTC, datetime

import pytest
from psycopg.errors import CheckViolation, InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def unidades(engine_app) -> tuple[int, int]:
    with engine_app.begin() as con:
        b = criar_bloco(con, 1)
        return criar_unidade(con, b, "101"), criar_unidade(con, b, "102")


def _conceder(con, unidade: int, papel: str = "admin") -> int:
    return con.execute(
        text("insert into unidade_papel (unidade_id, papel) values (:u, :p) returning id"),
        {"u": unidade, "p": papel},
    ).scalar_one()


def _retirar(con, papel_id: int) -> None:
    con.execute(text("update unidade_papel set retirado_em = now() where id = :i"), {"i": papel_id})


def test_ultimo_admin_nao_pode_ser_retirado(engine_app, unidades):
    with engine_app.begin() as con:
        p = _conceder(con, unidades[0])
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        _retirar(con, p)
    assert isinstance(erro.value.orig, CheckViolation)
    assert erro.value.orig.diag.constraint_name == "ultimo_admin"


def test_um_de_dois_admins_pode_sair(engine_app, unidades):
    with engine_app.begin() as con:
        p1 = _conceder(con, unidades[0])
        _conceder(con, unidades[1])
    with engine_app.begin() as con:
        _retirar(con, p1)


def test_comissao_pode_ser_retirada(engine_app, unidades):
    with engine_app.begin() as con:
        _conceder(con, unidades[0])
        c = _conceder(con, unidades[1], "comissao")
    with engine_app.begin() as con:
        _retirar(con, c)


def test_dois_admins_nao_se_retiram_ao_mesmo_tempo(engine_app, unidades):
    with engine_app.begin() as con:
        p1 = _conceder(con, unidades[0])
        p2 = _conceder(con, unidades[1])

    barreira = threading.Barrier(2)
    resultados: list[str] = []

    def retirar(papel_id: int) -> None:
        try:
            with engine_app.begin() as con:
                barreira.wait()
                _retirar(con, papel_id)
            resultados.append("ok")
        except IntegrityError:
            resultados.append("recusado")

    fios = [threading.Thread(target=retirar, args=(p,)) for p in (p1, p2)]
    for f in fios:
        f.start()
    for f in fios:
        f.join(10)
    assert sorted(resultados) == ["ok", "recusado"]


def test_datas_do_papel_sao_do_banco(engine_app, unidades):
    antes = datetime.now(UTC)
    with engine_app.begin() as con:
        _conceder(con, unidades[0])
        p = con.execute(
            text(
                "insert into unidade_papel (unidade_id, papel, concedido_em)"
                " values (:u, 'comissao', '2001-01-01 00:00+00') returning id"
            ),
            {"u": unidades[1]},
        ).scalar_one()
        con.execute(
            text("update unidade_papel set retirado_em = '2001-01-01 00:00+00' where id = :i"),
            {"i": p},
        )
        concedido, retirado = con.execute(
            text("select concedido_em, retirado_em from unidade_papel where id = :i"), {"i": p}
        ).one()
    assert abs((concedido - antes).total_seconds()) < 60
    assert abs((retirado - antes).total_seconds()) < 60


def test_papel_retirado_nao_volta(engine_app, unidades):
    with engine_app.begin() as con:
        _conceder(con, unidades[0])
        c = _conceder(con, unidades[1], "comissao")
        _retirar(con, c)
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        con.execute(text("update unidade_papel set retirado_em = null where id = :i"), {"i": c})


def test_app_nao_troca_um_papel_por_outro(engine_app, unidades):
    with engine_app.begin() as con:
        c = _conceder(con, unidades[1], "comissao")
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("update unidade_papel set papel = 'admin' where id = :i"), {"i": c})
    assert isinstance(erro.value.orig, InsufficientPrivilege)


# --- contatos da unidade ----------------------------------------------------------------------


def _ativar(con, unidade: int, **dados) -> None:
    valores = {"nome": "Fulano (fictício)", "celular": "81900000000", "email": None}
    valores.update(dados)
    con.execute(
        text(
            "update unidade set ativada_em = now(), responsavel_nome = :nome,"
            " celular = :celular, email = :email where id = :u"
        ),
        {"u": unidade, **valores},
    )


def test_unidade_ativada_com_contato(engine_app, unidades):
    with engine_app.begin() as con:
        _ativar(con, unidades[0], email="fulano@example.com")
        _ativar(con, unidades[1], celular="8190000000")


@pytest.mark.parametrize(
    "dados",
    [
        {"nome": None},
        {"celular": None},
        {"nome": ""},
        {"nome": " Fulano"},
        {"nome": "x" * 101},
        {"celular": "(81) 90000-0000"},
        {"celular": "819000"},
        {"celular": "819000000001"},
        {"email": "sem-arroba"},
        {"email": "Maiuscula@example.com"},
        {"email": "a@" + "b" * 260 + ".com"},
    ],
)
def test_contato_invalido_recusado(engine_app, unidades, dados):
    with pytest.raises(IntegrityError) as erro, engine_app.begin() as con:
        _ativar(con, unidades[0], **dados)
    assert isinstance(erro.value.orig, CheckViolation)
