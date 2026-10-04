import pytest
from sqlalchemy import text

pytestmark = pytest.mark.usefixtures("banco_limpo")


def test_saude_com_banco_vazio(cliente):
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "unidades": 0}


def test_saude_conta_as_unidades_do_banco(cliente, engine_app):
    with engine_app.begin() as con:
        b = con.execute(
            text("insert into bloco (numero, nome) values (2, 'Bloco 2') returning id")
        ).scalar_one()
        for numero in ("001", "002", "101"):
            con.execute(
                text(
                    "insert into unidade (bloco_id, numero, andar, senha_hash)"
                    " values (:b, :n, :a, 'h')"
                ),
                {"b": b, "n": numero, "a": int(numero[0])},
            )
    assert cliente.get("/api/saude").json() == {"status": "ok", "unidades": 3}


def test_saude_nao_e_cacheada(cliente):
    # O número precisa vir do banco a cada chamada, nunca de um cache da CDN.
    assert cliente.get("/api/saude").headers["cache-control"] == "no-store"
