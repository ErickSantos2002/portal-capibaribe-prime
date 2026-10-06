"""Regras de banco da revisão do M1 (migração 0003), como o usuário `app`.

- C4: aviso arquivado não recebe versão nova, mesmo com arquivar e corrigir ao mesmo tempo.
- U1: `aviso_leitura.versao_lida` (qual versão a unidade abriu por último); a primeira leitura
  (`lido_em`) não muda.
- C2: `entrada_tentativa` (bloqueio por login e IP) no lugar das colunas da unidade.
"""

import threading
import time

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from testes.apoio import criar_bloco, criar_unidade, restricao

pytestmark = pytest.mark.usefixtures("banco_limpo")


@pytest.fixture
def ids(engine_app) -> dict[str, int]:
    with engine_app.begin() as con:
        b = criar_bloco(con, 2)
        u = criar_unidade(con, b, "304")
        a = con.execute(
            text(
                "insert into aviso (publicado_por, publicado_como, para_todos)"
                " values (:u, 'comissao', true) returning id"
            ),
            {"u": u},
        ).scalar_one()
        _versao(con, a, u, 1)
    return {"u": u, "a": a}


def _versao(con, aviso: int, u: int, versao: int) -> None:
    con.execute(
        text(
            "insert into aviso_versao (aviso_id, versao, titulo, texto, criada_por)"
            " values (:a, :v, 'Título', :x, :u)"
        ),
        {"a": aviso, "v": versao, "x": f"Texto {versao}", "u": u},
    )


# --- C4 ---------------------------------------------------------------------------------------


def test_versao_nova_em_aviso_arquivado_recusada(engine_app, ids):
    with engine_app.begin() as con:
        con.execute(text("update aviso set arquivado_em = now() where id = :a"), {"a": ids["a"]})
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        _versao(con, ids["a"], ids["u"], 2)
    assert restricao(erro.value) == "aviso_versao_arquivado"


def test_arquivar_e_corrigir_ao_mesmo_tempo(engine_app, ids):
    """Arquivar (sem commit) segura a linha do aviso; a correção espera e, depois do commit do
    arquivamento, é recusada. Sem a trava no trigger, a versão entrava no aviso arquivado."""
    resultado: dict[str, BaseException | None] = {}

    with engine_app.connect() as arquivar:
        arquivar.begin()
        arquivar.execute(
            text("update aviso set arquivado_em = now() where id = :a"), {"a": ids["a"]}
        )

        def corrigir() -> None:
            try:
                with engine_app.begin() as con:
                    _versao(con, ids["a"], ids["u"], 2)
                resultado["erro"] = None
            except BaseException as e:  # noqa: BLE001 - levado para a thread principal
                resultado["erro"] = e

        fio = threading.Thread(target=corrigir)
        fio.start()
        _esperar_trava(engine_app)
        assert fio.is_alive(), "a correção devia estar esperando a trava do aviso"
        arquivar.commit()
        fio.join(10)

    erro = resultado["erro"]
    assert erro is not None, "a versão entrou num aviso arquivado"
    assert restricao(erro) == "aviso_versao_arquivado"
    with engine_app.connect() as con:
        assert (
            con.execute(
                text("select max(versao) from aviso_versao where aviso_id = :a"), {"a": ids["a"]}
            ).scalar_one()
            == 1
        )


def _esperar_trava(engine, segundos: float = 5) -> None:
    """Espera alguma conexão ficar parada esperando uma trava de linha."""
    fim = time.monotonic() + segundos
    while time.monotonic() < fim:
        with engine.connect() as con:
            if con.execute(
                text("select count(*) from pg_stat_activity where wait_event_type = 'Lock'")
            ).scalar_one():
                return
        time.sleep(0.05)
    raise AssertionError("ninguém ficou esperando a trava")


# --- U1 ---------------------------------------------------------------------------------------


def _ler(con, ids, versao: int | None = None) -> None:
    if versao is None:
        con.execute(
            text("insert into aviso_leitura (aviso_id, unidade_id) values (:a, :u)"),
            {"a": ids["a"], "u": ids["u"]},
        )
    else:
        con.execute(
            text(
                "insert into aviso_leitura (aviso_id, unidade_id, versao_lida) values (:a, :u, :v)"
            ),
            {"a": ids["a"], "u": ids["u"], "v": versao},
        )


def _leitura(con, ids):
    return con.execute(
        text("select lido_em, versao_lida from aviso_leitura where aviso_id = :a"),
        {"a": ids["a"]},
    ).one()


def test_versao_lida_sobe_e_lido_em_fica(engine_app, ids):
    with engine_app.begin() as con:
        _ler(con, ids, 1)
        _versao(con, ids["a"], ids["u"], 2)
    with engine_app.begin() as con:
        primeira = _leitura(con, ids)
    assert primeira.versao_lida == 1
    with engine_app.begin() as con:
        con.execute(text("update aviso_leitura set versao_lida = 2 where aviso_id = :a"), ids)
    with engine_app.begin() as con:
        depois = _leitura(con, ids)
    assert depois.versao_lida == 2
    assert depois.lido_em == primeira.lido_em


def test_versao_lida_nao_desce_nem_passa_da_atual(engine_app, ids):
    with engine_app.begin() as con:
        _versao(con, ids["a"], ids["u"], 2)
        _ler(con, ids, 2)
    with engine_app.begin() as con:
        con.execute(text("update aviso_leitura set versao_lida = 1 where aviso_id = :a"), ids)
        assert _leitura(con, ids).versao_lida == 2
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update aviso_leitura set versao_lida = 3 where aviso_id = :a"), ids)
    assert restricao(erro.value) == "aviso_leitura_versao"


def test_leitura_sem_versao_conta_a_atual(engine_app, ids):
    with engine_app.begin() as con:
        _versao(con, ids["a"], ids["u"], 2)
        _ler(con, ids)
        assert _leitura(con, ids).versao_lida == 2


def test_app_continua_sem_mexer_em_lido_em(engine_app, ids):
    with engine_app.begin() as con:
        _ler(con, ids, 1)
    with pytest.raises(ProgrammingError) as erro, engine_app.begin() as con:
        con.execute(text("update aviso_leitura set lido_em = now()"))
    assert isinstance(erro.value.orig, InsufficientPrivilege)


# --- C2 ---------------------------------------------------------------------------------------


def test_unidade_sem_contador_proprio(engine_app):
    with engine_app.connect() as con:
        colunas = set(
            con.execute(
                text(
                    "select column_name from information_schema.columns"
                    " where table_name = 'unidade'"
                )
            ).scalars()
        )
    assert not {"tentativas_falhas", "bloqueada_ate"} & colunas


def test_app_grava_e_apaga_tentativa(engine_app):
    hash_ = "a" * 64
    with engine_app.begin() as con:
        con.execute(
            text(
                "insert into entrada_tentativa (login, ip_hash, falhas_em, expira_em)"
                " values ('1101', :h, array[now()], now() + interval '15 minutes')"
            ),
            {"h": hash_},
        )
        con.execute(
            text("update entrada_tentativa set bloqueada_ate = now() where ip_hash = :h"),
            {"h": hash_},
        )
        con.execute(text("delete from entrada_tentativa where ip_hash = :h"), {"h": hash_})


@pytest.mark.parametrize(
    ("login", "ip_hash"),
    [("1101", "192.168.0.1"), ("9999", "a" * 64), ("1101", "A" * 64)],
)
def test_tentativa_so_guarda_hash_e_login_no_padrao(engine_app, login, ip_hash):
    with pytest.raises(DBAPIError), engine_app.begin() as con:
        con.execute(
            text(
                "insert into entrada_tentativa (login, ip_hash, expira_em) values (:l, :h, now())"
            ),
            {"l": login, "h": ip_hash},
        )
