"""Épico A · Primeiro acesso (H-01): `POST /api/acesso/primeiro-acesso`."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.modelos import Historico, Sessao, Unidade
from app.seguranca.senhas import SENHA_INICIAL, senha_confere
from app.seguranca.sessoes import NOME_COOKIE
from testes.conftest import BASE_URL, CABECALHO_PORTAL, COMUM, NAO_ATIVADA

ROTA = "/api/acesso/primeiro-acesso"
SENHA_NOVA = "casa-nova-2027"


def dados(**mudar) -> dict:
    base = {
        "senha_nova": SENHA_NOVA,
        "senha_nova_repetida": SENHA_NOVA,
        "responsavel_nome": "  Maria do Socorro (fictícia) ",
        "celular": "(81) 9 1234-5678",
        "email": "",
    }
    base.update(mudar)
    return base


def entrar_com_padrao(cliente: TestClient, login: str = NAO_ATIVADA) -> TestClient:
    resposta = cliente.post(
        "/api/acesso/entrar",
        json={"login": login, "senha": SENHA_INICIAL},
        headers=CABECALHO_PORTAL,
    )
    assert resposta.status_code == 200
    return cliente


def unidade(engine_app, login: str = NAO_ATIVADA) -> Unidade:
    with Session(engine_app) as db:
        return db.scalars(select(Unidade).where(Unidade.login == login)).one()


@pytest.mark.parametrize(
    ("mudar", "campo", "mensagem"),
    [
        (
            {"senha_nova": "curta", "senha_nova_repetida": "curta"},
            "senha_nova",
            "A senha nova precisa ter pelo menos 8 caracteres.",
        ),
        (
            {"senha_nova": SENHA_INICIAL, "senha_nova_repetida": SENHA_INICIAL},
            "senha_nova",
            "Escolha uma senha diferente da inicial, que todo mundo conhece.",
        ),
        (
            {"senha_nova_repetida": "outra-senha-qualquer"},
            "senha_nova_repetida",
            "As duas senhas estão diferentes. Escreva a mesma nas duas.",
        ),
        (
            {"responsavel_nome": "   "},
            "responsavel_nome",
            "Escreva o nome de quem responde pela unidade.",
        ),
        (
            {"celular": "1234"},
            "celular",
            "Confira o celular: DDD e número, como (81) 9 1234-5678.",
        ),
        ({"email": "sem-arroba"}, "email", "Confira o e-mail, ou deixe em branco."),
    ],
)
def test_h01_recusa_e_explica_em_linguagem_simples(
    cliente, predio, engine_app, mudar, campo, mensagem
):
    resposta = entrar_com_padrao(cliente).post(ROTA, json=dados(**mudar), headers=CABECALHO_PORTAL)
    assert resposta.status_code == 422
    assert {"campo": campo, "mensagem": mensagem} in resposta.json()["campos"]
    # Nada mudou: continua não ativada.
    assert unidade(engine_app).ativada_em is None


def test_h01_recusa_nao_devolve_a_senha_digitada(cliente, predio):
    resposta = entrar_com_padrao(cliente).post(
        ROTA, json=dados(senha_nova_repetida="segredo-que-nao-volta"), headers=CABECALHO_PORTAL
    )
    assert "segredo-que-nao-volta" not in resposta.text


def test_h01_concluir_ativa_a_unidade_com_data(cliente, predio, engine_app):
    resposta = entrar_com_padrao(cliente).post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    assert resposta.status_code == 200
    assert resposta.json()["precisa_trocar_senha"] is False
    assert resposta.json()["unidade"]["login"] == NAO_ATIVADA
    u = unidade(engine_app)
    assert u.ativada_em is not None
    assert u.precisa_trocar_senha is False
    assert senha_confere(u.senha_hash, SENHA_NOVA)
    assert (u.responsavel_nome, u.celular, u.email) == (
        "Maria do Socorro (fictícia)",
        "81912345678",
        None,
    )


def test_h01_email_e_opcional_mas_guardado_se_vier(cliente, predio, engine_app):
    entrar_com_padrao(cliente).post(
        ROTA, json=dados(email=" Familia@Exemplo.com "), headers=CABECALHO_PORTAL
    )
    assert unidade(engine_app).email == "familia@exemplo.com"


def test_h01_email_pode_faltar_no_corpo(cliente, predio):
    corpo = dados()
    del corpo["email"]
    resposta = entrar_com_padrao(cliente).post(ROTA, json=corpo, headers=CABECALHO_PORTAL)
    assert resposta.status_code == 200


def test_h01_depois_de_concluir_cai_no_mural(cliente, predio):
    """Sessão completa: as rotas de unidade logada passam a responder."""
    entrar_com_padrao(cliente).post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    assert cliente.get("/api/acesso/eu").json()["precisa_trocar_senha"] is False
    assert cliente.get("/api/minha-unidade").status_code == 200


def test_h01_fica_no_historico(cliente, predio, engine_app):
    entrar_com_padrao(cliente).post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    with Session(engine_app) as db:
        registro = db.scalars(select(Historico).where(Historico.acao == "primeiro_acesso")).one()
    assert registro.unidade_id == predio[NAO_ATIVADA]
    assert (registro.entidade, registro.entidade_id) == ("unidade", predio[NAO_ATIVADA])
    assert "Socorro" not in str(registro.detalhes)


def test_h01_cookie_novo_e_quem_entrou_antes_com_mudar123_perde_o_acesso(
    cliente, predio, engine_app
):
    intruso = entrar_com_padrao(TestClient(app, base_url=BASE_URL))
    resposta = entrar_com_padrao(cliente).post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    assert resposta.headers["set-cookie"].startswith(f"{NOME_COOKIE}=")
    assert cliente.get("/api/acesso/eu").status_code == 200
    assert intruso.get("/api/acesso/eu").status_code == 401
    with Session(engine_app) as db:
        abertas = db.scalars(select(Sessao).where(Sessao.encerrada_em.is_(None))).all()
    assert len(abertas) == 1


def test_h01_depois_de_concluir_mudar123_nao_entra_mais(cliente, predio):
    entrar_com_padrao(cliente).post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    resposta = cliente.post(
        "/api/acesso/entrar",
        json={"login": NAO_ATIVADA, "senha": SENHA_INICIAL},
        headers=CABECALHO_PORTAL,
    )
    assert resposta.status_code == 401
    novo = cliente.post(
        "/api/acesso/entrar",
        json={"login": NAO_ATIVADA, "senha": SENHA_NOVA},
        headers=CABECALHO_PORTAL,
    )
    assert novo.json()["precisa_trocar_senha"] is False


def test_h01_repetir_o_primeiro_acesso_e_409(logar, predio):
    resposta = logar(COMUM).post(ROTA, json=dados())
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "primeiro_acesso_ja_feito"


def test_h01_sem_sessao_e_401(cliente, predio):
    resposta = cliente.post(ROTA, json=dados(), headers=CABECALHO_PORTAL)
    assert resposta.status_code == 401


def test_h01_sem_cabecalho_portal_e_403(cliente, predio):
    entrar_com_padrao(cliente)
    assert cliente.post(ROTA, json=dados()).status_code == 403
