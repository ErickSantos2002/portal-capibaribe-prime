"""Ajustes do M2 · "Receber os avisos por e-mail" em Minha unidade (resposta do Erick ao item 7
de `duvidas-m2.md`; plano `docs/superpowers/plans/m2-ajustes.md`).

A opção vem ligada; desligar para as cópias dos avisos, mas o e-mail continua cadastrado e o
"esqueci a senha" continua funcionando.
"""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modelos import Bloco, Unidade
from app.servicos import notificacoes
from testes.conftest import CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_email_apoio import email_ligado, smtp  # noqa: F401 - fixtures
from testes.test_m2_notificacoes import _aviso_no_banco, _email
from testes.test_minha_unidade import APAGAR, unidade

CAMINHO = "/api/minha-unidade/avisos-por-email"


@pytest.fixture
def fabrica(engine_app):
    return lambda: Session(engine_app)


# --- banco ---------------------------------------------------------------------------------------


@pytest.mark.usefixtures("banco_limpo")
def test_unidade_nova_pelo_orm_nasce_recebendo(engine_app):
    # O gotcha do SQLAlchemy: atributo nulo no INSERT desligaria o DEFAULT do banco.
    with Session(engine_app) as db:
        bloco = Bloco(numero=1, nome="Bloco 1")
        db.add(bloco)
        db.flush()
        nova = Unidade(bloco_id=bloco.id, numero="101", andar=1, senha_hash="h")
        db.add(nova)
        db.commit()
        db.refresh(nova)
        assert nova.receber_avisos_email is True


@pytest.mark.usefixtures("predio")
def test_banco_nao_aceita_opcao_nula(engine_app):
    with pytest.raises(IntegrityError), engine_app.begin() as con:
        con.execute(
            text("update unidade set receber_avisos_email = null where login = :l"), {"l": COMUM}
        )


# --- API -----------------------------------------------------------------------------------------


def test_minha_unidade_mostra_a_opcao_ligada_por_padrao(logar, predio):
    assert logar(COMUM).get("/api/minha-unidade").json()["receber_avisos_email"] is True


def test_desligar_e_ligar_de_novo(logar, predio, engine_app):
    c = logar(COMUM)
    resposta = c.put(CAMINHO, json={"receber": False})
    assert resposta.status_code == 200
    assert resposta.json()["receber_avisos_email"] is False
    assert unidade(engine_app).receber_avisos_email is False
    assert c.get("/api/minha-unidade").json()["receber_avisos_email"] is False

    assert c.put(CAMINHO, json={"receber": True}).json()["receber_avisos_email"] is True
    assert unidade(engine_app).receber_avisos_email is True


def test_desligar_nao_apaga_o_email(logar, predio, engine_app):
    _email(engine_app, COMUM, "comum@example.com")
    corpo = logar(COMUM).put(CAMINHO, json={"receber": False}).json()
    assert corpo["email"] == "comum@example.com"
    assert unidade(engine_app).email == "comum@example.com"


def test_so_muda_a_propria_unidade(logar, predio, engine_app):
    logar(COMUM).put(CAMINHO, json={"receber": False})
    assert unidade(engine_app, COMISSAO).receber_avisos_email is True


@pytest.mark.parametrize("corpo", [{}, {"receber": None}, {"receber": "talvez"}, {"x": 1}])
def test_corpo_invalido_e_422(logar, predio, engine_app, corpo):
    assert logar(COMUM).put(CAMINHO, json=corpo).status_code == 422
    assert unidade(engine_app).receber_avisos_email is True


def test_sem_sessao_e_401_e_sessao_restrita_e_403(cliente, logar, predio):
    resposta = cliente.put(CAMINHO, json={"receber": False}, headers=CABECALHO_PORTAL)
    assert resposta.status_code == 401
    assert logar(NAO_ATIVADA).put(CAMINHO, json={"receber": False}).status_code == 403


def test_apagar_dados_volta_a_opcao_para_ligada(logar, predio, engine_app):
    c = logar(COMUM)
    c.put(CAMINHO, json={"receber": False})
    assert c.post("/api/minha-unidade/apagar-dados", json=APAGAR).status_code == 204
    assert unidade(engine_app).receber_avisos_email is True


# --- quem recebe ---------------------------------------------------------------------------------


def _desligar(engine, login: str) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set receber_avisos_email = false where login = :l"), {"l": login}
        )


@pytest.mark.usefixtures("predio")
def test_email_pula_quem_desligou(engine_app, fabrica):
    _email(engine_app, COMUM, "comum@example.com")
    _email(engine_app, COMISSAO, "comissao@example.com")
    _desligar(engine_app, COMUM)
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        destinos = notificacoes.destinos_email(db, notificacoes.carregar_aviso(db, aviso_id))
    assert [d.login for d in destinos] == [COMISSAO]


@pytest.mark.usefixtures("predio")
def test_quem_desligou_o_email_continua_com_o_push(engine_app, fabrica):
    from testes.test_m2_notificacoes import _sessao_inscrita

    sessao = _sessao_inscrita(engine_app, COMUM, 1)
    _desligar(engine_app, COMUM)
    aviso_id = _aviso_no_banco(engine_app, fabrica)
    with fabrica() as db:
        destinos = notificacoes.destinos_push(db, notificacoes.carregar_aviso(db, aviso_id))
    assert sessao in [d.sessao_id for d in destinos]


def test_esqueci_a_senha_funciona_com_a_opcao_desligada(cliente, predio, engine_app, email_ligado):
    _email(engine_app, COMUM, "comum@example.com")
    _desligar(engine_app, COMUM)
    resposta = cliente.post(
        "/api/acesso/recuperacao", json={"login": COMUM}, headers=CABECALHO_PORTAL
    )
    assert resposta.status_code == 202
    assert [m["To"] for m in email_ligado.mensagens] == ["comum@example.com"]
