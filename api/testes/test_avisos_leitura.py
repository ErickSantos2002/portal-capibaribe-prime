"""H-16 · Saber quem leu: "Lido por X de Y unidades" e a lista das que não leram."""

import pytest
from sqlalchemy import text

from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, publicar

pytestmark = pytest.mark.usefixtures("predio")


def _leitura(cliente, aviso_id: int) -> dict:
    resposta = cliente.get(f"/api/avisos/{aviso_id}/leitura")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# --- H-16: uma unidade conta como "leu" quando abre o aviso ------------------------------------


def test_abrir_conta_como_lido(logar):
    aviso = publicar(logar(COMISSAO))
    comum = logar(COMUM)
    assert comum.post(f"/api/avisos/{aviso['id']}/lido").status_code == 204
    leitura = _leitura(logar(ADMIN), aviso["id"])
    assert (leitura["lidos"], leitura["total"]) == (2, 320)
    logins = [u["login"] for u in leitura["nao_leram"]]
    assert len(logins) == 318
    assert COMUM not in logins and COMISSAO not in logins
    assert logins == sorted(logins)
    assert leitura["nao_leram"][0] == {"login": "1001", "bloco": 1, "apartamento": "001"}


def test_abrir_de_novo_nao_conta_duas_vezes(logar, engine_app):
    aviso = publicar(logar(COMISSAO))
    comum = logar(COMUM)
    for _ in range(3):
        assert comum.post(f"/api/avisos/{aviso['id']}/lido").status_code == 204
    with engine_app.connect() as con:
        assert con.execute(text("select count(*) from aviso_leitura")).scalar_one() == 2
    assert _leitura(logar(ADMIN), aviso["id"])["lidos"] == 2


def test_lido_de_aviso_inexistente(logar):
    resposta = logar(COMUM).post("/api/avisos/999/lido")
    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "aviso_nao_encontrado"


# --- H-16: gestão vê "Lido por X de Y" ---------------------------------------------------------


def test_total_e_do_destino(logar):
    aviso = publicar(logar(COMISSAO), para_todos=False, blocos=[1])
    logar(COMUM).post(f"/api/avisos/{aviso['id']}/lido")
    # A gestão abriu aviso de outro bloco: não entra na conta (2304 é do Bloco 2).
    logar(COMISSAO).post(f"/api/avisos/{aviso['id']}/lido")
    leitura = _leitura(logar(ADMIN), aviso["id"])
    assert (leitura["lidos"], leitura["total"], len(leitura["nao_leram"])) == (1, 64, 63)
    assert {u["bloco"] for u in leitura["nao_leram"]} == {1}


def test_total_conta_so_unidades_ativas(logar, engine_app):
    with engine_app.begin() as con:
        con.execute(text("update unidade set ativa = false where login = '1102'"))
    aviso = publicar(logar(COMISSAO))
    leitura = _leitura(logar(ADMIN), aviso["id"])
    assert leitura["total"] == 319
    assert "1102" not in [u["login"] for u in leitura["nao_leram"]]


def test_contagem_no_aviso_so_para_a_gestao(logar):
    aviso = publicar(logar(COMISSAO))
    logar(COMUM).post(f"/api/avisos/{aviso['id']}/lido")
    assert logar(ADMIN).get(f"/api/avisos/{aviso['id']}").json()["leitura"] == {
        "lidos": 2,
        "total": 320,
    }
    assert logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()["leitura"] is None


def test_leitura_de_aviso_inexistente(logar):
    resposta = logar(ADMIN).get("/api/avisos/999/leitura")
    assert resposta.status_code == 404
