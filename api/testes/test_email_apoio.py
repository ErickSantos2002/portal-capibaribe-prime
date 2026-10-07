"""Apoio dos testes do épico B do M2: um servidor SMTP falso e o e-mail ligado por variável de
ambiente. **Nenhum teste fala com o Gmail**: `smtplib.SMTP_SSL` e `smtplib.SMTP` são trocados
por uma conexão que só guarda as mensagens.
"""

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage

import pytest

from app import configuracao

USUARIO = "portal@example.com"
SENHA_APP = "senha-de-app-de-teste"
URL_BASE = "https://portal.example.com"


@dataclass
class ServidorFalso:
    """O que as conexões falsas viram: conexões abertas, mensagens e o que recusar."""

    conexoes: list["ConexaoFalsa"] = field(default_factory=list)
    # Endereços que o servidor recusa (550 no RCPT TO): falha só daquele destino.
    recusar: set[str] = field(default_factory=set)
    # Cai a conexão ao mandar a mensagem número N (1, 2, …).
    cair_na: int | None = None
    # Recusa o login (senha de app errada).
    recusar_login: bool = False
    # Mensagem recusada depois do DATA, por endereço: {para: (código, texto)}. O Gmail usa isto
    # tanto para "mensagem grande demais" (só aquela) quanto para "cota do dia estourada".
    recusar_mensagem: dict[str, tuple[int, bytes]] = field(default_factory=dict)
    # Remetente recusado (MAIL FROM) a partir da mensagem número N.
    recusar_remetente_na: int | None = None
    # Chamado a cada mensagem aceita (para os testes mexerem no relógio, por exemplo).
    ao_mandar: list = field(default_factory=list)

    @property
    def mensagens(self) -> list[EmailMessage]:
        return [m for c in self.conexoes for m in c.mensagens]

    def enviadas(self) -> int:
        return sum(len(c.tentativas) for c in self.conexoes)


class ConexaoFalsa:
    servidor: ServidorFalso

    def __init__(self, host: str, port: int = 0, *, timeout: float | None = None, context=None):
        self.host, self.porta, self.timeout, self.contexto = host, port, timeout, context
        self.tls = isinstance(self, ConexaoFalsaSSL)
        self.starttls_contexto = None
        self.login_feito: tuple[str, str] | None = None
        self.mensagens: list[EmailMessage] = []
        self.tentativas: list[str] = []
        self.fechada = False
        self.servidor.conexoes.append(self)

    def starttls(self, *, context=None):
        self.tls = True
        self.starttls_contexto = context

    def login(self, usuario: str, senha: str):
        if not self.tls:
            raise AssertionError("login antes do TLS")
        if self.servidor.recusar_login:
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
        self.login_feito = (usuario, senha)

    def send_message(self, mensagem: EmailMessage, *args, **kwargs):
        assert self.login_feito is not None, "mandou sem login"
        assert not self.fechada
        para = mensagem["To"]
        self.tentativas.append(para)
        if self.servidor.cair_na == self.servidor.enviadas():
            self.fechada = True
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
        if para in self.servidor.recusar:
            raise smtplib.SMTPRecipientsRefused({para: (550, b"5.1.1 No such user")})
        na = self.servidor.recusar_remetente_na
        if na is not None and self.servidor.enviadas() >= na:
            raise smtplib.SMTPSenderRefused(
                550, b"5.4.5 Daily user sending limit exceeded.", "portal@example.com"
            )
        if para in self.servidor.recusar_mensagem:
            raise smtplib.SMTPDataError(*self.servidor.recusar_mensagem[para])
        self.mensagens.append(mensagem)
        for chamar in self.servidor.ao_mandar:
            chamar(mensagem)
        return {}

    def quit(self):
        self.fechada = True

    def close(self):
        self.fechada = True


class ConexaoFalsaSSL(ConexaoFalsa):
    pass


@pytest.fixture
def smtp(monkeypatch) -> ServidorFalso:
    servidor = ServidorFalso()
    ConexaoFalsa.servidor = servidor
    monkeypatch.setattr(smtplib, "SMTP_SSL", ConexaoFalsaSSL)
    monkeypatch.setattr(smtplib, "SMTP", ConexaoFalsa)
    return servidor


@pytest.fixture
def email_ligado(monkeypatch, smtp) -> ServidorFalso:
    """E-mail configurado como em produção, mas falando com o SMTP falso."""
    monkeypatch.setenv("PORTAL_SMTP_USUARIO", USUARIO)
    monkeypatch.setenv("PORTAL_SMTP_SENHA_APP", SENHA_APP)
    monkeypatch.setenv("PORTAL_URL_BASE", URL_BASE)
    configuracao.limpar_cache()
    yield smtp
    configuracao.limpar_cache()


@pytest.fixture
def email_desligado(monkeypatch, smtp) -> ServidorFalso:
    for nome in ("PORTAL_SMTP_USUARIO", "PORTAL_SMTP_SENHA_APP", "PORTAL_URL_BASE"):
        monkeypatch.delenv(nome, raising=False)
    configuracao.limpar_cache()
    yield smtp
    configuracao.limpar_cache()
