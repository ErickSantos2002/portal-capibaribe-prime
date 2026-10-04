"""Regras que o próprio banco garante nas tabelas de acesso."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.usefixtures("banco_limpo")


def _bloco(con, numero: int) -> int:
    return con.execute(
        text("insert into bloco (numero, nome) values (:n, :nome) returning id"),
        {"n": numero, "nome": f"Bloco {numero}"},
    ).scalar_one()


def _unidade(con, bloco_id: int, numero: str, **extra) -> int:
    colunas = {"bloco_id": bloco_id, "numero": numero, "andar": int(numero[0]), "senha_hash": "h"}
    colunas.update(extra)
    nomes = ", ".join(colunas)
    valores = ", ".join(f":{c}" for c in colunas)
    return con.execute(
        text(f"insert into unidade ({nomes}) values ({valores}) returning id"), colunas
    ).scalar_one()


def _login(con, unidade_id: int) -> str:
    return con.execute(
        text("select login from unidade where id = :u"), {"u": unidade_id}
    ).scalar_one()


def test_login_gerado_pelo_banco(engine_app):
    with engine_app.begin() as con:
        u = _unidade(con, _bloco(con, 1), "101")
        assert _login(con, u) == "1101"


def test_login_ignora_valor_mandado_pela_aplicacao(engine_app):
    with engine_app.begin() as con:
        u = _unidade(con, _bloco(con, 1), "007", login="9999")
        assert _login(con, u) == "1007"
        con.execute(text("update unidade set login = 'xyz' where id = :u"), {"u": u})
        assert _login(con, u) == "1007"


def test_login_acompanha_troca_de_numero_do_bloco(engine_app):
    with engine_app.begin() as con:
        b = _bloco(con, 1)
        u = _unidade(con, b, "204")
        con.execute(text("update bloco set numero = 3 where id = :b"), {"b": b})
        assert _login(con, u) == "3204"


@pytest.mark.parametrize("numero", ["12", "1234", "abc", "1a1"])
def test_numero_da_unidade_tem_tres_digitos(engine_app, numero):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(
            text(
                "insert into unidade (bloco_id, numero, andar, senha_hash) values (:b, :n, 1, 'h')"
            ),
            {"b": _bloco(con, 1), "n": numero},
        )


@pytest.mark.parametrize("andar", [-1, 8])
def test_andar_entre_terreo_e_setimo(engine_app, andar):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _unidade(con, _bloco(con, 1), "101", andar=andar)


@pytest.mark.parametrize("numero", [0, 10])
def test_numero_do_bloco_de_1_a_9(engine_app, numero):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        _bloco(con, numero)


def test_unidade_unica_dentro_do_bloco(engine_app):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        b = _bloco(con, 1)
        _unidade(con, b, "101")
        _unidade(con, b, "101")


def test_um_papel_em_vigor_por_tipo(engine_app):
    with engine_app.begin() as con:
        u = _unidade(con, _bloco(con, 1), "101")
        inserir = text("insert into unidade_papel (unidade_id, papel) values (:u, 'admin')")
        con.execute(inserir, {"u": u})
        # Retirado o papel, a unidade pode recebê-lo de novo.
        con.execute(text("update unidade_papel set retirado_em = now()"))
        con.execute(inserir, {"u": u})
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(inserir, {"u": u})


def test_padroes_da_unidade_nova(engine_app):
    with engine_app.begin() as con:
        u = _unidade(con, _bloco(con, 1), "101")
        linha = con.execute(
            text(
                "select ativa, precisa_trocar_senha, tentativas_falhas, ativada_em"
                " from unidade where id = :u"
            ),
            {"u": u},
        ).one()
    assert tuple(linha) == (True, True, 0, None)
