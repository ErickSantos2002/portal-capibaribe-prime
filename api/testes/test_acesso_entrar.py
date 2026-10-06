"""Épico A · Entrar (H-02) e bloqueio por tentativas (H-03): `POST /api/acesso/entrar`."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modelos import Sessao, Unidade
from app.seguranca.senhas import SENHA_INICIAL
from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA

MSG_CREDENCIAIS = "Bloco, apartamento ou senha incorretos. Confira e tente de novo."


def entrar(cliente, login: str, senha: str, **extra):
    return cliente.post(
        "/api/acesso/entrar",
        json={"login": login, "senha": senha},
        headers={**CABECALHO_PORTAL, **extra},
    )


def unidade(engine_app, login: str) -> Unidade:
    with Session(engine_app) as db:
        return db.scalars(select(Unidade).where(Unidade.login == login)).one()


# --- H-02 · entrar no dia a dia -----------------------------------------------------------------


def test_h02_senha_certa_abre_a_sessao_e_devolve_eu(cliente, predio):
    resposta = entrar(cliente, COMUM, f"senha-{COMUM}")
    assert resposta.status_code == 200
    assert resposta.json() == {
        "unidade": {"login": COMUM, "bloco": 1, "apartamento": "203"},
        "papeis": [],
        "gestao": False,
        "admin": False,
        "precisa_trocar_senha": False,
    }
    cookie = resposta.headers["set-cookie"]
    assert cookie.startswith(f"{NOME_COOKIE}=")
    assert "HttpOnly" in cookie and "Secure" in cookie and "samesite=lax" in cookie.lower()
    # O cliente guardou o cookie: a próxima requisição já está logada (abre o mural).
    assert cliente.get("/api/acesso/eu").json()["unidade"]["login"] == COMUM


def test_h02_eu_traz_os_papeis_da_gestao(cliente, predio):
    eu = entrar(cliente, COMISSAO, f"senha-{COMISSAO}").json()
    assert (eu["papeis"], eu["gestao"], eu["admin"]) == (["comissao"], True, False)


def test_h02_sessao_dura_180_dias(cliente, predio):
    cookie = entrar(cliente, COMUM, f"senha-{COMUM}").headers["set-cookie"]
    assert f"Max-Age={180 * 24 * 3600}" in cookie


def test_h02_guarda_so_a_descricao_do_aparelho(cliente, predio, engine_app):
    agente = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Version/17.0 Safari/604.1"
    entrar(cliente, COMUM, f"senha-{COMUM}", **{"user-agent": agente})
    with Session(engine_app) as db:
        assert db.scalars(select(Sessao.aparelho)).one() == "iPhone · Safari"


@pytest.mark.parametrize(
    ("login", "senha"),
    [
        ("5799", "qualquer-coisa"),  # login no formato, mas não existe (posição 99)
        (COMUM, "senha-errada"),  # existe, senha errada
        (NAO_ATIVADA, "senha-errada"),  # não ativada, senha errada
    ],
)
def test_h02_login_inexistente_e_senha_errada_dao_a_mesma_resposta(cliente, predio, login, senha):
    resposta = entrar(cliente, login, senha)
    assert resposta.status_code == 401
    assert resposta.json() == {
        "codigo": "credenciais_invalidas",
        "mensagem": MSG_CREDENCIAIS,
        "tentativas_restantes": 4,
    }
    assert "set-cookie" not in resposta.headers


def test_h02_unidade_desativada_responde_como_inexistente(cliente, predio, engine_dono):
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": "5101"})
    resposta = entrar(cliente, "5101", SENHA_INICIAL)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "credenciais_invalidas"


def test_h02_login_inexistente_tambem_confere_um_hash(cliente, predio, monkeypatch):
    """O tempo de resposta não separa "não existe" de "senha errada"."""
    from app.seguranca import senhas

    chamadas: list[str] = []
    original = senhas.senha_confere
    monkeypatch.setattr(senhas, "senha_confere", lambda h, s: chamadas.append(s) or original(h, s))
    entrar(cliente, "5799", "chute")
    assert chamadas == ["chute"]


def test_h02_formato_de_login_invalido_e_422_sem_ecoar_a_senha(cliente, predio):
    resposta = entrar(cliente, "11011", "minha-senha-secreta")
    assert resposta.status_code == 422
    assert resposta.json()["campos"][0]["campo"] == "login"
    assert "minha-senha-secreta" not in resposta.text


def test_h02_sem_cabecalho_portal_e_recusado(cliente, predio):
    resposta = cliente.post("/api/acesso/entrar", json={"login": COMUM, "senha": "x"})
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "requisicao_recusada"


# --- H-01 · entrar com mudar123 leva ao primeiro acesso -----------------------------------------


def test_h01_unidade_nunca_acessada_entra_com_sessao_restrita(cliente, predio):
    resposta = entrar(cliente, NAO_ATIVADA, SENHA_INICIAL)
    assert resposta.status_code == 200
    assert resposta.json()["precisa_trocar_senha"] is True
    # Sessão restrita: não abre o mural.
    assert cliente.get("/api/minha-unidade").json()["codigo"] == "primeiro_acesso_pendente"


def test_h01_fechou_no_meio_e_entrou_de_novo_volta_ao_primeiro_acesso(cliente, predio):
    entrar(cliente, NAO_ATIVADA, SENHA_INICIAL)
    cliente.post("/api/acesso/sair", headers=CABECALHO_PORTAL)
    assert entrar(cliente, NAO_ATIVADA, SENHA_INICIAL).json()["precisa_trocar_senha"] is True


def test_h02_entrar_de_novo_abre_outro_aparelho_sem_derrubar_o_primeiro(
    cliente, predio, engine_app
):
    entrar(cliente, COMUM, f"senha-{COMUM}")
    entrar(cliente, COMUM, f"senha-{COMUM}")
    with Session(engine_app) as db:
        abertas = db.scalars(select(Sessao).where(Sessao.encerrada_em.is_(None))).all()
    # Entrar de novo abre outra sessão (outro aparelho) sem derrubar a anterior.
    assert len(abertas) == 2
