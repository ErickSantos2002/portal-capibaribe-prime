"""Avisar a gestão, moderar, e-mail do primeiro aviso e categorias dos classificados (spec de
20/10/2026, seções 3.2, 4 e 9)."""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.servicos import notificacoes
from testes.apoio_classificados import anunciar, ids_da_lista
from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_email_apoio import (  # noqa: F401 - fixtures
    URL_BASE,
    email_desligado,
    email_ligado,
    smtp,
)

MOTIVO = "Parece golpe"


def _avisos(engine) -> list[tuple]:
    with engine.connect() as con:
        return [
            tuple(r) for r in con.execute(text("select anuncio_id, unidade_id from aviso_anuncio"))
        ]


def _historico(engine, acao: str) -> list[dict]:
    with engine.connect() as con:
        return [
            dict(r._mapping)
            for r in con.execute(
                text(
                    "select unidade_id, entidade, entidade_id, detalhes from historico"
                    " where acao = :a order by id"
                ),
                {"a": acao},
            )
        ]


# --- avisar -----------------------------------------------------------------------------------


def test_avisar_uma_vez_aberto_por_unidade(logar, predio, engine_app):
    a = anunciar(logar(COMUM))
    vizinho = logar(COMISSAO)
    assert vizinho.post(f"/api/classificados/{a}/aviso", json={"motivo": MOTIVO}).status_code == 204
    assert vizinho.post(f"/api/classificados/{a}/aviso", json={}).status_code == 204
    assert _avisos(engine_app) == [(a, predio[COMISSAO])]
    assert vizinho.get(f"/api/classificados/{a}").json()["ja_avisei"] is True
    assert logar(ADMIN).post(f"/api/classificados/{a}/aviso").status_code == 204
    assert len(_avisos(engine_app)) == 2


def test_motivo_com_301_letras_422(logar, predio):
    a = anunciar(logar(COMUM))
    r = logar(ADMIN).post(f"/api/classificados/{a}/aviso", json={"motivo": "a" * 301})
    assert r.status_code == 422


def test_morador_nao_ve_os_avisos_e_a_gestao_ve_sem_a_placa(logar, predio):
    a = anunciar(logar(COMUM))
    logar(COMISSAO).post(f"/api/classificados/{a}/aviso", json={"motivo": MOTIVO})
    assert logar(COMUM).get(f"/api/classificados/{a}").json()["avisos"] is None
    avisos = logar(ADMIN).get(f"/api/classificados/{a}").json()["avisos"]
    assert [v["motivo"] for v in avisos] == [MOTIVO]
    assert "unidade" not in avisos[0] and "2304" not in str(avisos)


def test_contagem_e_filtro_com_aviso_so_para_a_gestao(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    a = anunciar(dono, titulo="Com aviso")
    b = anunciar(dono, titulo="Sem aviso")
    logar(COMISSAO).post(f"/api/classificados/{a}/aviso")
    assert logar(COMUM).get("/api/classificados").json()["com_aviso"] is None
    gestao = logar(ADMIN)
    lista = gestao.get("/api/classificados").json()
    assert lista["com_aviso"] == 1
    assert {i["id"]: i["avisos_abertos"] for i in lista["itens"]} == {a: 1, b: 0}
    assert ids_da_lista(gestao, com_aviso=True) == [a]
    # O morador que pede com_aviso recebe a lista comum.
    assert ids_da_lista(dono, com_aviso=True) == [b, a]
    # Vencido com aviso aberto continua no filtro da gestão.
    from testes.apoio_classificados import envelhecer

    envelhecer(engine_superusuario, "anuncio", "vence_em", a, 1)
    assert ids_da_lista(gestao, com_aviso=True) == [a]
    assert ids_da_lista(gestao) == [b]


# --- moderar ----------------------------------------------------------------------------------


def test_so_a_gestao_esconde_e_resolve(logar, predio, engine_app):
    a = anunciar(logar(COMUM))
    logar(ADMIN).post(f"/api/classificados/{a}/aviso")
    with engine_app.connect() as con:
        aviso = con.execute(text("select id from aviso_anuncio")).scalar_one()
    assert logar(COMUM).post(f"/api/classificados/{a}/esconder").status_code == 403
    assert logar(COMUM).post(f"/api/classificados/avisos/{aviso}/resolver").status_code == 403
    assert logar(COMISSAO).post(f"/api/classificados/avisos/{aviso}/resolver").status_code == 204
    assert logar(COMISSAO).post(f"/api/classificados/{a}/esconder").status_code == 204
    # Repetir não muda nada.
    assert logar(ADMIN).post(f"/api/classificados/{a}/esconder").status_code == 204


def test_esconder_tira_da_lista_resolve_os_avisos_e_registra(logar, predio, engine_app):
    a = anunciar(logar(COMUM), titulo="Golpe do sofá")
    logar(ADMIN).post(f"/api/classificados/{a}/aviso", json={"motivo": MOTIVO})
    assert logar(COMISSAO).post(f"/api/classificados/{a}/esconder").status_code == 204
    assert ids_da_lista(logar(ADMIN)) == []
    assert logar(ADMIN).get("/api/classificados").json()["com_aviso"] == 0
    with engine_app.connect() as con:
        assert (
            con.execute(
                text("select count(*) from aviso_anuncio where resolvido_em is null")
            ).scalar_one()
            == 0
        )
    registro = _historico(engine_app, "classificado_escondido")
    assert registro == [
        {"unidade_id": predio[COMISSAO], "entidade": "anuncio", "entidade_id": a, "detalhes": {}}
    ]
    assert "Golpe" not in str(_historico(engine_app, "classificado_aviso_resolvido"))
    # Escondido não recebe aviso novo.
    assert logar(COMISSAO).post(f"/api/classificados/{a}/aviso").status_code == 404


def test_esconder_o_que_nao_existe_404(logar, predio):
    assert logar(ADMIN).post("/api/classificados/99999/esconder").status_code == 404
    assert logar(ADMIN).post("/api/classificados/avisos/99999/resolver").status_code == 404


# --- categorias --------------------------------------------------------------------------------


def test_so_o_admin_mexe_em_categoria(logar, predio):
    r = logar(COMISSAO).post("/api/classificados/categorias", json={"nome": "Livros"})
    assert r.status_code == 403
    r = logar(ADMIN).post("/api/classificados/categorias", json={"nome": "Livros"})
    assert r.status_code == 201
    nomes = [c["nome"] for c in logar(COMUM).get("/api/classificados/categorias").json()["itens"]]
    assert nomes[-2:] == ["Livros", "Outros"]


def test_renomear_e_repetida_da_409(logar, predio, engine_app):
    admin = logar(ADMIN)
    r = admin.put("/api/classificados/categorias/2", json={"nome": "Eletrodomésticos e cozinha"})
    assert r.status_code == 200 and r.json()["nome"] == "Eletrodomésticos e cozinha"
    r = admin.post("/api/classificados/categorias", json={"nome": "móveis"})
    assert r.status_code == 409 and r.json()["codigo"] == "categoria_ja_existe"
    assert _historico(engine_app, "categoria_classificado_renomeada")[0]["detalhes"] == {
        "categoria": "Eletrodomésticos e cozinha"
    }


# --- e-mail do primeiro aviso -----------------------------------------------------------------


def _com_email(engine, login: str, email: str) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set email = :e where login = :l"), {"e": email, "l": login}
        )


def _corpo(mensagem) -> str:
    return mensagem.get_body(("plain",)).get_content() + mensagem.get_body(("html",)).get_content()


@pytest.fixture
def anuncio(logar, predio, engine_app) -> int:
    _com_email(engine_app, ADMIN, "admin@example.com")
    _com_email(engine_app, COMISSAO, "comissao@example.com")
    return anunciar(logar(COMUM), titulo="Sofá de 3 lugares")


def test_primeiro_aviso_manda_um_email_para_cada_admin(logar, email_ligado, anuncio, engine_app):
    logar(COMISSAO).post(f"/api/classificados/{anuncio}/aviso", json={"motivo": MOTIVO})
    logar(ADMIN).post(f"/api/classificados/{anuncio}/aviso")
    assert email_ligado.enviadas() == 1
    mensagem = email_ligado.mensagens[0]
    assert mensagem["To"] == "admin@example.com"
    assert mensagem["Subject"] == "Portal Capibaribe Prime: aviso num anúncio dos classificados"
    corpo = _corpo(mensagem)
    assert f"{URL_BASE}/classificados/{anuncio}" in corpo
    assert "Sofá de 3 lugares" in corpo and "Móveis" in corpo
    assert MOTIVO not in corpo and "2304" not in corpo and "1203" not in corpo
    reservas = _historico(engine_app, "classificado_aviso_email")
    assert reservas == [
        {
            "unidade_id": None,
            "entidade": "anuncio",
            "entidade_id": anuncio,
            "detalhes": {"reservados": 1},
        }
    ]
    with Session(engine_app) as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 1


def test_cota_esgotada_nao_manda(logar, email_ligado, anuncio, monkeypatch):
    monkeypatch.setattr(notificacoes, "LIMITE_EMAILS_24H", 0)
    logar(COMISSAO).post(f"/api/classificados/{anuncio}/aviso")
    assert email_ligado.enviadas() == 0


def test_email_desligado_ou_falhando_nao_levanta(logar, email_ligado, anuncio, caplog):
    email_ligado.recusar_login = True
    with caplog.at_level(logging.INFO):
        assert logar(COMISSAO).post(f"/api/classificados/{anuncio}/aviso").status_code == 204
    texto = " ".join(r.getMessage() for r in caplog.records)
    assert caplog.records and "Sofá" not in texto and "admin@example.com" not in texto
