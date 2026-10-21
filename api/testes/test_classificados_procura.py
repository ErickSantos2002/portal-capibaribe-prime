"""O tipo "Procura" (resposta do Erick, 20/10/2026, pergunta 1): quem procura algo anuncia que
procura. Sem preço, não fica reservado, e encerra com "Encontrei" ou "Desisti"."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from testes.apoio import restricao
from testes.apoio_classificados import NOVO, anunciar, criar_anuncio, ids_da_lista
from testes.conftest import ADMIN, COMUM

PROCURA = {**NOVO, "tipo": "procura", "titulo": "Berço usado", "preco_centavos": None}


def test_anunciar_procura_e_filtrar(logar, predio):
    a = anunciar(logar(COMUM), **PROCURA)
    venda = anunciar(logar(COMUM), titulo="Sofá")
    leitor = logar(ADMIN)
    assert ids_da_lista(leitor, tipo="procura") == [a]
    assert set(ids_da_lista(leitor)) == {a, venda}
    assert leitor.get(f"/api/classificados/{a}").json()["tipo"] == "procura"


def test_procura_nao_tem_preco(logar, predio):
    r = logar(COMUM).post("/api/classificados", json={**PROCURA, "preco_centavos": 100})
    assert r.status_code == 422


def test_procura_nao_fica_reservado_pela_api(logar, predio):
    a = anunciar(logar(COMUM), **PROCURA)
    r = logar(COMUM).post(f"/api/classificados/{a}/reservar")
    assert r.status_code == 409 and r.json()["codigo"] == "procura_nao_reserva"


def test_procura_nao_fica_reservado_no_banco(engine_app, banco_limpo, ids):
    with engine_app.begin() as con:
        b = criar_anuncio(con, ids["u"], tipo="procura", preco=None)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update anuncio set situacao = 'reservado' where id = :a"), {"a": b})
    assert restricao(erro.value) == "anuncio_procura_reservado"


def test_reservado_nao_vira_procura(engine_app, banco_limpo, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"], tipo="troca", preco=None)
        con.execute(text("update anuncio set situacao = 'reservado' where id = :a"), {"a": a})
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(text("update anuncio set tipo = 'procura' where id = :a"), {"a": a})
    assert restricao(erro.value) == "anuncio_procura_reservado"


def test_motivos_do_procura_e_dos_outros(logar, predio):
    dono = logar(COMUM)
    a = anunciar(dono, **PROCURA)
    r = dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "vendi"})
    assert r.status_code == 422
    r = dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "encontrei"})
    assert r.status_code == 200 and r.json()["motivo_encerramento"] == "encontrei"
    b = anunciar(dono, titulo="Mesa")
    assert (
        dono.post(f"/api/classificados/{b}/encerrar", json={"motivo": "encontrei"}).status_code
        == 422
    )


def test_motivo_encontrei_so_no_procura_no_banco(engine_app, banco_limpo, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(
            text(
                "update anuncio set situacao = 'encerrado', motivo_encerramento = 'encontrei'"
                " where id = :a"
            ),
            {"a": a},
        )
    assert restricao(erro.value) == "anuncio_motivo_do_tipo"
