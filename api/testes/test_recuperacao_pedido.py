"""Pedido de link de recuperação, depois da resposta (H-04; contrato do M2, seção 4.3; spec do
épico B, seção 2.5). `processar_pedido` com o SMTP falso e o banco de teste."""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import hashlib
import logging
import re

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.servicos import notificacoes
from app.servicos.recuperacao import processar_pedido
from testes.conftest import ADMIN, COMUM, NAO_ATIVADA
from testes.test_avisos_apoio import historico
from testes.test_email_apoio import (  # noqa: F401 - fixtures
    SENHA_APP,
    URL_BASE,
    email_desligado,
    email_ligado,
    smtp,
)

pytestmark = pytest.mark.usefixtures("predio")

EMAIL = "morador@example.com"


@pytest.fixture
def fabrica(engine_app) -> sessionmaker[Session]:
    return sessionmaker(engine_app, expire_on_commit=False)


def _com_email(engine, login: str, email: str = EMAIL) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set email = :e where login = :l"), {"e": email, "l": login}
        )


def _tokens(engine, login: str) -> list[dict]:
    with engine.connect() as con:
        return [
            dict(linha)
            for linha in con.execute(
                text(
                    "select t.token_hash, t.usado_em from token_recuperacao t"
                    " join unidade u on u.id = t.unidade_id where u.login = :l order by t.id"
                ),
                {"l": login},
            ).mappings()
        ]


def _token_do_email(mensagem) -> str:
    corpo = mensagem.get_body(("plain",)).get_content()
    achado = re.search(re.escape(URL_BASE) + r"/redefinir-senha#token=([A-Za-z0-9_-]+)", corpo)
    assert achado, corpo
    return achado[1]


def _pedidos_no_historico(engine) -> list[dict]:
    return historico(engine, "recuperacao_pedida")


def test_unidade_com_email_recebe_o_link(engine_app, fabrica, email_ligado, predio):
    _com_email(engine_app, COMUM)
    processar_pedido(COMUM, fabrica)
    assert [m["To"] for m in email_ligado.mensagens] == [EMAIL]
    token = _token_do_email(email_ligado.mensagens[0])
    assert len(token) >= 43
    # O banco guarda só o SHA-256; o token em texto existe só no e-mail.
    assert _tokens(engine_app, COMUM) == [
        {"token_hash": hashlib.sha256(token.encode()).hexdigest(), "usado_em": None}
    ]
    assert _pedidos_no_historico(engine_app) == [
        {
            "unidade_id": None,
            "entidade": "unidade",
            "entidade_id": predio[COMUM],
            "detalhes": {"enviado": True, "motivo": None},
        }
    ]


def test_email_sai_depois_do_commit(engine_app, fabrica, email_ligado):
    _com_email(engine_app, COMUM)
    visto: list[int] = []
    email_ligado.ao_mandar.append(lambda m: visto.append(len(_tokens(engine_app, COMUM))))
    processar_pedido(COMUM, fabrica)
    # Outra conexão já via o token quando o e-mail saiu: a trava da cota já tinha sido solta.
    assert visto == [1]


def test_login_que_nao_existe_nao_faz_nada(engine_app, fabrica, email_ligado):
    processar_pedido("5799", fabrica)
    assert email_ligado.mensagens == []
    assert _pedidos_no_historico(engine_app) == []


def test_unidade_desativada_conta_como_inexistente(engine_app, engine_dono, fabrica, email_ligado):
    _com_email(engine_app, COMUM)
    with engine_dono.begin() as con:
        con.execute(text("delete from unidade_papel"))
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": COMUM})
    processar_pedido(COMUM, fabrica)
    assert email_ligado.mensagens == []
    assert _pedidos_no_historico(engine_app) == []


@pytest.mark.parametrize(("login", "email"), [(COMUM, None), (NAO_ATIVADA, EMAIL)])
def test_sem_email_ou_sem_primeiro_acesso(engine_app, fabrica, email_ligado, predio, login, email):
    if email:
        _com_email(engine_app, login, email)
    processar_pedido(login, fabrica)
    assert email_ligado.mensagens == []
    assert _tokens(engine_app, login) == []
    assert _pedidos_no_historico(engine_app) == [
        {
            "unidade_id": None,
            "entidade": "unidade",
            "entidade_id": predio[login],
            "detalhes": {"enviado": False, "motivo": "sem_email"},
        }
    ]


def test_email_desligado(engine_app, fabrica, email_desligado):
    _com_email(engine_app, COMUM)
    processar_pedido(COMUM, fabrica)
    assert email_desligado.conexoes == []
    assert _tokens(engine_app, COMUM) == []
    assert _pedidos_no_historico(engine_app)[0]["detalhes"] == {
        "enviado": False,
        "motivo": "desligado",
    }


def test_cota_do_dia_esgotada(engine_app, fabrica, email_ligado, monkeypatch):
    _com_email(engine_app, COMUM)
    monkeypatch.setattr(notificacoes, "LIMITE_EMAILS_24H", 0)
    processar_pedido(COMUM, fabrica)
    assert email_ligado.mensagens == []
    assert _tokens(engine_app, COMUM) == []
    assert _pedidos_no_historico(engine_app)[0]["detalhes"] == {"enviado": False, "motivo": "cota"}


def test_limite_de_3_por_hora_e_historico_uma_vez_por_hora(engine_app, fabrica, email_ligado):
    _com_email(engine_app, COMUM)
    for _ in range(4):
        processar_pedido(COMUM, fabrica)
    assert len(email_ligado.mensagens) == 3
    assert len(_tokens(engine_app, COMUM)) == 3
    # Um script contra os 320 logins não enche o histórico: um registro por unidade por hora.
    assert [h["detalhes"] for h in _pedidos_no_historico(engine_app)] == [
        {"enviado": True, "motivo": None}
    ]


def test_limite_registrado_quando_e_o_primeiro_da_hora(
    engine_app, engine_superusuario, fabrica, email_ligado
):
    _com_email(engine_app, COMUM)
    for _ in range(3):
        processar_pedido(COMUM, fabrica)
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(text("update historico set ocorrido_em = now() - interval '61 minutes'"))
    processar_pedido(COMUM, fabrica)
    assert [h["detalhes"] for h in _pedidos_no_historico(engine_app)][-1] == {
        "enviado": False,
        "motivo": "limite",
    }


def test_cada_unidade_tem_o_proprio_limite(engine_app, fabrica, email_ligado):
    _com_email(engine_app, COMUM, "comum@example.com")
    _com_email(engine_app, ADMIN, "admin@example.com")
    for _ in range(3):
        processar_pedido(COMUM, fabrica)
    processar_pedido(ADMIN, fabrica)
    assert [m["To"] for m in email_ligado.mensagens][-1] == "admin@example.com"


def test_falha_no_smtp_nao_levanta_e_o_log_nao_tem_dado(engine_app, fabrica, email_ligado, caplog):
    _com_email(engine_app, COMUM)
    email_ligado.recusar_login = True
    with caplog.at_level(logging.DEBUG):
        processar_pedido(COMUM, fabrica)
    assert "SMTPAuthenticationError" in caplog.text
    hash_ = _tokens(engine_app, COMUM)[0]["token_hash"]
    for dado in (COMUM, EMAIL, SENHA_APP, hash_):
        assert dado not in caplog.text


def test_erro_no_banco_nao_levanta(caplog):
    def quebrada():
        raise RuntimeError("banco fora do ar")

    with caplog.at_level(logging.ERROR):
        processar_pedido(COMUM, quebrada)
    assert "RuntimeError" in caplog.text
    assert COMUM not in caplog.text
