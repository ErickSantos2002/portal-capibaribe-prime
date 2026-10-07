"""Cópia do aviso por e-mail (H-13; spec do épico B, seção 2.2), com o SMTP falso.

Unidade: o `ENVIADOR` com destinos e cota de mentira (sem banco). Integração: publicar pela API
e conferir o que o SMTP falso recebeu e o que ficou em `notificacao_envio`.
"""

# ruff: noqa: F811 - as fixtures do SMTP falso vêm de test_email_apoio
import logging
import re
import smtplib
import ssl

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.servicos import email, notificacoes
from app.servicos.notificacoes import AvisoParaNotificar, DestinoEmail, Resultado
from testes.test_avisos_apoio import COMISSAO, publicar
from testes.test_email_apoio import (  # noqa: F401 - fixtures
    SENHA_APP,
    USUARIO,
    email_desligado,
    email_ligado,
    smtp,
)

AVISO = AvisoParaNotificar(
    aviso_id=9,
    titulo="Reunião de condomínio",
    texto="Quinta, 19h.",
    categoria="reuniao",
    publicado_por=1,
    para_todos=True,
    blocos=(),
)


def _destinos(quantos: int) -> list[DestinoEmail]:
    return [
        DestinoEmail(unidade_id=i, login=f"1{i:03d}", email=f"morador{i}@example.com")
        for i in range(1, quantos + 1)
    ]


@pytest.fixture
def destinos(monkeypatch):
    """`destinos(n)`: o enviador passa a ver n unidades com e-mail (sem banco)."""

    def definir(quantos: int) -> list[DestinoEmail]:
        lista = _destinos(quantos)
        monkeypatch.setattr(email, "destinos_email", lambda db, aviso: lista)
        monkeypatch.setattr(
            email, "publicacao_do_aviso", lambda db, aviso_id: "Publicado pela Comissão"
        )
        return lista

    return definir


def _resultado(cota: int = 1000, salvos: list | None = None, **extra) -> Resultado:
    def reservar(n: int) -> int:
        return min(n, cota)

    def salvar(r: Resultado) -> None:
        if salvos is not None:
            salvos.append(dict(r.contagens()))

    return Resultado(_reservar=reservar, _salvar=salvar, **extra)


# --- ligado ------------------------------------------------------------------------------------


def test_ligado_segue_a_configuracao(email_desligado, monkeypatch):
    assert email.ENVIADOR.ligado() is False
    monkeypatch.setenv("PORTAL_SMTP_USUARIO", USUARIO)
    monkeypatch.setenv("PORTAL_SMTP_SENHA_APP", SENHA_APP)
    monkeypatch.setenv("PORTAL_URL_BASE", "https://portal.example.com")
    assert email.ENVIADOR.ligado() is True


# --- unidade -----------------------------------------------------------------------------------


def test_uma_conexao_para_o_lote_e_uma_mensagem_por_unidade(email_ligado, destinos):
    lista = destinos(3)
    resultado = _resultado()
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert len(email_ligado.conexoes) == 1
    conexao = email_ligado.conexoes[0]
    assert (conexao.host, conexao.porta) == ("smtp.gmail.com", 465)
    assert isinstance(conexao.contexto, ssl.SSLContext)
    assert conexao.timeout and conexao.timeout <= 30
    assert conexao.login_feito == (USUARIO, SENHA_APP)
    assert conexao.fechada
    assert [m.get_all("To") for m in email_ligado.mensagens] == [[d.email] for d in lista]
    assert resultado.contagens() | {"reservados": 0} == {
        "destinos": 3,
        "entregues": 3,
        "falhas": 0,
        "removidas": 0,
        "pulados": 0,
        "reservados": 0,
    }
    assert resultado.reservados == 3


def test_outra_porta_usa_starttls(email_ligado, destinos, monkeypatch):
    from app import configuracao

    monkeypatch.setenv("PORTAL_SMTP_PORTA", "587")
    configuracao.limpar_cache()
    destinos(1)
    email.ENVIADOR.enviar(None, AVISO, _resultado())
    conexao = email_ligado.conexoes[0]
    assert conexao.porta == 587
    assert isinstance(conexao.starttls_contexto, ssl.SSLContext)
    assert len(conexao.mensagens) == 1


def test_reserva_antes_de_mandar_e_o_que_nao_cabe_e_pulado(email_ligado, destinos):
    destinos(5)
    resultado = _resultado(cota=2)
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert len(email_ligado.mensagens) == 2
    assert (resultado.entregues, resultado.pulados, resultado.reservados) == (2, 3, 2)


def test_sem_cota_nem_conecta(email_ligado, destinos):
    destinos(4)
    resultado = _resultado(cota=0)
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert email_ligado.conexoes == []
    assert (resultado.destinos, resultado.pulados, resultado.entregues) == (4, 4, 0)


def test_sem_destinos_nem_conecta(email_ligado, destinos):
    destinos(0)
    resultado = _resultado()
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert email_ligado.conexoes == []
    assert resultado.contagens()["destinos"] == 0


def test_recusa_de_um_destinatario_conta_falha_e_segue(email_ligado, destinos):
    lista = destinos(3)
    email_ligado.recusar = {lista[1].email}
    resultado = _resultado()
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.falhas) == (2, 1)
    assert len(email_ligado.conexoes) == 1


def test_mensagem_recusada_comum_e_falha_so_daquela(email_ligado, destinos):
    lista = destinos(3)
    email_ligado.recusar_mensagem = {lista[0].email: (552, b"5.3.4 Message size exceeds limit")}
    resultado = _resultado()
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.falhas) == (2, 1)


@pytest.mark.parametrize(
    "recusa",
    [
        (550, b"5.4.5 Daily user sending quota exceeded."),
        (421, b"4.7.0 Try again later, closing connection."),
        (451, b"4.7.1 Temporary rate limit"),
    ],
    ids=["cota-do-dia", "421", "4.7.x"],
)
def test_cota_ou_limite_do_gmail_na_mensagem_interrompe(email_ligado, destinos, recusa):
    # Continuar seria bater na mesma parede centenas de vezes (revisão do épico B, item 1).
    lista = destinos(5)
    email_ligado.recusar_mensagem = {d.email: recusa for d in lista[1:]}
    resultado = _resultado()
    with pytest.raises(smtplib.SMTPDataError):
        email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.falhas) == (1, 0)
    assert email_ligado.enviadas() == 2


def test_remetente_recusado_interrompe(email_ligado, destinos):
    destinos(5)
    email_ligado.recusar_remetente_na = 3
    resultado = _resultado()
    with pytest.raises(smtplib.SMTPSenderRefused):
        email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.falhas) == (2, 0)
    assert email_ligado.enviadas() == 3


def test_interrompido_devolve_a_reserva_do_que_nem_foi_tentado(email_ligado, destinos):
    # Revisão, item 3: só a mensagem que estava saindo (pode ter saído) fica na reserva.
    destinos(10)
    email_ligado.cair_na = 4
    resultado = _resultado()
    with pytest.raises(smtplib.SMTPServerDisconnected):
        email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.reservados) == (3, 4)


def test_senha_de_app_errada_devolve_a_reserva_inteira(email_ligado, destinos):
    destinos(10)
    email_ligado.recusar_login = True
    resultado = _resultado()
    with pytest.raises(smtplib.SMTPAuthenticationError):
        email.ENVIADOR.enviar(None, AVISO, resultado)
    assert resultado.reservados == 0


def test_queda_da_conexao_interrompe_com_as_contagens_ate_ali(email_ligado, destinos):
    destinos(5)
    email_ligado.cair_na = 3
    resultado = _resultado()
    with pytest.raises(Exception, match="closed"):
        email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.falhas) == (2, 0)
    assert email_ligado.conexoes[0].fechada


def test_tempo_esgotado_para_e_conta_o_resto_como_pulado(email_ligado, destinos, monkeypatch):
    destinos(5)
    relogio = {"agora": 0.0}
    monkeypatch.setattr(notificacoes.time, "monotonic", lambda: relogio["agora"])
    # Cada mensagem "leva" 10 s; o prazo é de 25 s: cabem 3.
    email_ligado.ao_mandar.append(lambda m: relogio.update(agora=relogio["agora"] + 10))
    resultado = _resultado(prazo=25.0)
    email.ENVIADOR.enviar(None, AVISO, resultado)
    assert (resultado.entregues, resultado.pulados) == (3, 2)
    assert resultado.entregues + resultado.falhas + resultado.pulados == resultado.destinos


def test_progresso_salvo_a_cada_25(email_ligado, destinos):
    destinos(60)
    salvos: list = []
    email.ENVIADOR.enviar(None, AVISO, _resultado(salvos=salvos))
    assert [s["entregues"] for s in salvos] == [25, 50]


# --- integração: publicar pela API ------------------------------------------------------------


def _com_email(engine, *logins: str) -> None:
    with engine.begin() as con:
        for login in logins:
            con.execute(
                text(
                    "update unidade set precisa_trocar_senha = false,"
                    " ativada_em = coalesce(ativada_em, now()),"
                    " responsavel_nome = coalesce(responsavel_nome, 'Fictício'),"
                    " celular = coalesce(celular, '81900000000'),"
                    " email = :e where login = :l"
                ),
                {"e": f"u{login}@example.com", "l": login},
            )


def _envio_email(engine, aviso_id: int) -> dict:
    with engine.connect() as con:
        return dict(
            con.execute(
                text(
                    "select situacao, destinos, entregues, falhas, pulados, reservados"
                    " from notificacao_envio where aviso_id = :a and canal = 'email'"
                ),
                {"a": aviso_id},
            )
            .mappings()
            .one()
        )


@pytest.mark.usefixtures("predio")
def test_publicar_para_o_bloco_1_manda_so_para_o_bloco_1(logar, engine_app, email_ligado):
    _com_email(engine_app, "1101", "1203", "1305", "2101", COMISSAO)
    aviso = publicar(
        logar(COMISSAO),
        titulo="Falta d'água",
        texto="## Atenção\n**Hoje** das 8h às 12h.",
        para_todos=False,
        blocos=[1],
    )
    # H-13: só as unidades do Bloco 1 com e-mail; nem o Bloco 2, nem quem publicou.
    assert sorted(m["To"] for m in email_ligado.mensagens) == [
        "u1101@example.com",
        "u1203@example.com",
        "u1305@example.com",
    ]
    assert len(email_ligado.conexoes) == 1
    mensagem = email_ligado.mensagens[0]
    assert mensagem["Subject"] == "Falta d'água"
    corpo = mensagem.get_body(("plain",)).get_content()
    assert f"https://portal.example.com/avisos/{aviso['id']}" in corpo
    assert re.search(r"Publicado pela Comissão em [0-9]{2}/[0-9]{2}, às [0-9]{1,2}h[0-9]{2}", corpo)
    assert _envio_email(engine_app, aviso["id"]) == {
        "situacao": "concluido",
        "destinos": 3,
        "entregues": 3,
        "falhas": 0,
        "pulados": 0,
        "reservados": 3,
    }


@pytest.mark.usefixtures("predio")
def test_html_injetado_no_titulo_e_no_texto_sai_escapado(logar, engine_app, email_ligado):
    _com_email(engine_app, "1203")
    publicar(
        logar(COMISSAO),
        titulo="<img src=x onerror=alert(1)>",
        texto="<script>alert(1)</script> e **<b>x</b>**",
    )
    html = email_ligado.mensagens[0].get_body(("html",)).get_content()
    assert "<script>" not in html and "<img" not in html and "<b>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<strong>&lt;b&gt;x&lt;/b&gt;</strong>" in html


@pytest.mark.usefixtures("predio")
def test_senha_de_app_errada_interrompe_e_o_log_nao_mostra_dado(
    logar, engine_app, email_ligado, caplog
):
    _com_email(engine_app, "1203")
    email_ligado.recusar_login = True
    with caplog.at_level(logging.INFO):
        aviso = publicar(logar(COMISSAO))
    envio = _envio_email(engine_app, aviso["id"])
    assert envio["situacao"] == "interrompido"
    assert envio["entregues"] == 0
    # Nada saiu: a reserva volta e a cota do dia fica livre (revisão, item 3).
    assert envio["reservados"] == 0
    with Session(engine_app) as db:
        assert notificacoes.emails_nas_ultimas_24h(db) == 0
    assert "SMTPAuthenticationError" in caplog.text
    for dado in (SENHA_APP, "u1203@example.com", USUARIO):
        assert dado not in caplog.text
