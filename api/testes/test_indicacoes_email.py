"""E-mail para a administração no primeiro aviso aberto de uma indicação (spec de 18/10/2026,
seção 8). Pela rota (o `TestClient` roda o trabalho de depois da resposta) e com o SMTP falso:
nenhum teste fala com o Gmail."""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import logging

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.servicos import notificacoes
from app.servicos.indicacoes_email import avisar_administracao
from testes.apoio_indicacoes import indicar
from testes.conftest import ADMIN, COMISSAO, COMUM
from testes.test_email_apoio import (  # noqa: F401 - fixtures
    URL_BASE,
    email_desligado,
    email_ligado,
    smtp,
)

pytestmark = pytest.mark.usefixtures("predio")

MOTIVO = "O número não atende"


def _com_email(engine, login: str, email: str, *, receber: bool = True) -> None:
    with engine.begin() as con:
        con.execute(
            text("update unidade set email = :e, receber_avisos_email = :r where login = :l"),
            {"e": email, "r": receber, "l": login},
        )


def _avisar(cliente, prestador: int):
    resposta = cliente.post(f"/api/indicacoes/{prestador}/aviso", json={"motivo": MOTIVO})
    assert resposta.status_code == 204, resposta.text


def _corpo(mensagem) -> str:
    return mensagem.get_body(("plain",)).get_content() + mensagem.get_body(("html",)).get_content()


@pytest.fixture
def prestador(logar, engine_app) -> int:
    _com_email(engine_app, ADMIN, "admin@example.com")
    _com_email(engine_app, COMISSAO, "comissao@example.com")
    return indicar(logar(ADMIN), nome="Marcenaria Exemplo")


def test_primeiro_aviso_manda_um_email_para_cada_admin(logar, email_ligado, prestador):
    _avisar(logar(COMUM), prestador)
    assert email_ligado.enviadas() == 1
    mensagem = email_ligado.mensagens[0]
    assert mensagem["To"] == "admin@example.com"
    assert mensagem["Subject"] == "Portal Capibaribe Prime: aviso numa indicação"
    corpo = _corpo(mensagem)
    assert f"{URL_BASE}/indicacoes/{prestador}" in corpo
    assert "Marcenaria Exemplo" in corpo and "Móveis planejados" in corpo
    assert "Abrir a indicação" in corpo
    # Nem a placa de quem avisou, nem o motivo.
    assert "1203" not in corpo and "203" not in corpo and MOTIVO not in corpo


def test_segundo_aviso_aberto_do_mesmo_prestador_nao_manda(logar, email_ligado, prestador):
    _avisar(logar(COMUM), prestador)
    _avisar(logar(COMISSAO), prestador)
    _avisar(logar(COMUM), prestador)  # repetido
    assert email_ligado.enviadas() == 1


def test_depois_de_resolvido_o_proximo_aviso_manda_de_novo(
    logar, engine_app, email_ligado, prestador
):
    _avisar(logar(COMUM), prestador)
    with engine_app.connect() as con:
        aviso = con.execute(text("select id from aviso_servico")).scalar_one()
    assert logar(ADMIN).post(f"/api/indicacoes/avisos/{aviso}/resolver").status_code == 204
    _avisar(logar(COMUM), prestador)
    assert email_ligado.enviadas() == 2


def test_comissao_nao_recebe(logar, email_ligado, prestador):
    _avisar(logar(COMUM), prestador)
    assert [m["To"] for m in email_ligado.mensagens] == ["admin@example.com"]


def test_admin_sem_email_nao_recebe(logar, engine_app, email_ligado, prestador):
    with engine_app.begin() as con:
        con.execute(text("update unidade set email = null where login = :l"), {"l": ADMIN})
    _avisar(logar(COMUM), prestador)
    assert email_ligado.enviadas() == 0


def test_admin_que_desligou_os_avisos_do_mural_recebe(logar, engine_app, email_ligado, prestador):
    _com_email(engine_app, ADMIN, "admin@example.com", receber=False)
    _avisar(logar(COMUM), prestador)
    assert email_ligado.enviadas() == 1


def test_cota_esgotada_nao_manda(logar, engine_app, email_ligado, prestador, monkeypatch):
    monkeypatch.setattr(notificacoes, "LIMITE_EMAILS_24H", 0)
    _avisar(logar(COMUM), prestador)
    assert email_ligado.enviadas() == 0
    with engine_app.connect() as con:
        assert con.execute(text("select emails_reservados from aviso_servico")).scalar_one() == 0


def test_emails_reservados_entram_na_cota(logar, engine_app, email_ligado, prestador):
    with Session(engine_app) as db:
        antes = notificacoes.emails_nas_ultimas_24h(db)
    _avisar(logar(COMUM), prestador)
    with Session(engine_app) as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == antes + 1
    with engine_app.connect() as con:
        assert con.execute(text("select emails_reservados from aviso_servico")).scalar_one() == 1


def test_email_desligado_nao_levanta(logar, email_desligado, prestador):
    _avisar(logar(COMUM), prestador)
    assert email_desligado.enviadas() == 0


def test_falha_no_smtp_nao_levanta_e_o_log_nao_tem_o_nome(
    logar, engine_app, email_ligado, prestador, caplog
):
    email_ligado.recusar_login = True
    with caplog.at_level(logging.INFO):
        _avisar(logar(COMUM), prestador)
    assert email_ligado.mensagens == []
    assert caplog.records, "a falha precisa ir para o log"
    texto = " ".join(r.getMessage() for r in caplog.records)
    assert "Marcenaria" not in texto and "admin@example.com" not in texto


def test_aviso_que_nao_existe_nao_levanta(engine_app, email_ligado):
    avisar_administracao(999999, sessionmaker(engine_app, expire_on_commit=False))
    assert email_ligado.enviadas() == 0
