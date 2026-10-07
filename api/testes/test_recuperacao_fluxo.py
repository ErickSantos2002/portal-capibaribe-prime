"""O "esqueci a senha" de ponta a ponta, pelas rotas (H-04): pedir → e-mail → conferir →
senha nova → entrar. E a resposta do pedido, igual com e sem e-mail."""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import re

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import text

from app.esquemas.recuperacao import MSG_PEDIDO, PedirRecuperacao
from app.rotas import recuperacao as rota
from app.servicos import recuperacao
from testes.conftest import ADMIN, CABECALHO_PORTAL, COMISSAO, COMUM
from testes.test_email_apoio import (  # noqa: F401 - fixtures
    URL_BASE,
    email_ligado,
    smtp,
)

pytestmark = pytest.mark.usefixtures("predio")


def _post(cliente, caminho: str, corpo: dict):
    return cliente.post(caminho, json=corpo, headers=CABECALHO_PORTAL)


def test_esqueci_a_senha_de_ponta_a_ponta(cliente, logar, engine_app, email_ligado):
    with engine_app.begin() as con:
        con.execute(
            text("update unidade set email = 'socorro@example.com' where login = :l"), {"l": COMUM}
        )
    celular_antigo = logar(COMUM)

    pedido = _post(cliente, "/api/acesso/recuperacao", {"login": COMUM})
    assert pedido.status_code == 202
    [mensagem] = email_ligado.mensagens
    assert mensagem["To"] == "socorro@example.com"
    corpo = mensagem.get_body(("plain",)).get_content()
    token = re.search(re.escape(URL_BASE) + r"/redefinir-senha#token=(\S+)", corpo)[1]

    assert _post(cliente, "/api/acesso/recuperacao/conferir", {"token": token}).json() == {
        "unidade": {"login": COMUM, "bloco": 1, "apartamento": "203"}
    }
    senha = "minha senha nova"
    nova = _post(
        cliente,
        "/api/acesso/recuperacao/redefinir",
        {"token": token, "senha_nova": senha, "senha_nova_repetida": senha},
    )
    assert nova.status_code == 200
    assert cliente.get("/api/acesso/eu").status_code == 200
    assert celular_antigo.get("/api/acesso/eu").status_code == 401

    cliente.cookies.clear()
    assert _post(cliente, "/api/acesso/entrar", {"login": COMUM, "senha": senha}).status_code == 200


@pytest.mark.parametrize("com_email", [True, False])
def test_resposta_igual_com_e_sem_email(cliente, engine_app, email_ligado, com_email):
    # 1203 com ou sem e-mail, 2304 sem e-mail, 5799 não existe: a mesma resposta, byte a byte.
    if com_email:
        with engine_app.begin() as con:
            con.execute(
                text("update unidade set email = 'x@example.com' where login = :l"), {"l": COMUM}
            )
    respostas = {
        login: _post(cliente, "/api/acesso/recuperacao", {"login": login})
        for login in (COMUM, COMISSAO, "5799")
    }
    vistas = {(r.status_code, r.text, r.headers.get("content-length")) for r in respostas.values()}
    assert vistas == {
        (202, '{"mensagem":"' + MSG_PEDIDO + '"}', str(len(respostas[COMUM].content)))
    }
    assert len(email_ligado.mensagens) == (1 if com_email else 0)


def test_o_pedido_so_agenda_e_nada_roda_dentro_da_requisicao(monkeypatch):
    # O tempo de resposta não pode revelar quem tem e-mail: a rota só agenda o trabalho, que
    # roda depois da resposta. Com e sem e-mail, o mesmo caminho dentro da requisição.
    chamados: list[str] = []
    monkeypatch.setattr(recuperacao, "processar_pedido", chamados.append)
    for login in (ADMIN, COMUM, "5799"):
        tarefas = BackgroundTasks()
        resposta = rota.pedir(PedirRecuperacao(login=login), tarefas)
        assert resposta.mensagem == MSG_PEDIDO
        assert chamados == []
        assert [(t.func, t.args) for t in tarefas.tasks] == [(chamados.append, (login,))]
