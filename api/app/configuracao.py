"""Configuração de push e e-mail, lida das variáveis de ambiente (spec do M2, seção 6).

Regra: **sem configuração, o canal fica desligado e nada quebra.** Variável ausente, em branco
ou com valor inválido desliga só aquele canal (com um aviso no log que nunca mostra o valor); o
resto do Portal funciona igual. Por isso o M2 pode ir ao ar antes da conta do Gmail existir.

- `PORTAL_VAPID_PRIVADA`: chave privada VAPID, 32 bytes em base64url
  (`python -m app.comandos.gerar_chaves_vapid`).
- `PORTAL_VAPID_CONTATO`: contato do remetente para os serviços de push (`mailto:` ou `https://`).
- `PORTAL_SMTP_USUARIO`: a conta Gmail do Portal (ADR-0006).
- `PORTAL_SMTP_SENHA_APP`: a senha de app dessa conta (nunca a senha da conta).
- `PORTAL_SMTP_HOST`, `PORTAL_SMTP_PORTA`: opcionais; padrão `smtp.gmail.com` e 465 (TLS direto).
- `PORTAL_URL_BASE`: endereço do Portal nos links dos e-mails, ex.:
  `https://portal-capibaribe-prime.vercel.app`.

A chave pública VAPID não é variável: sai da privada, então as duas nunca ficam trocadas.

`PORTAL_URL_BASE` existe para o link do e-mail **nunca** vir do cabeçalho `Host` da requisição:
quem pede "esqueci a senha" escolheria para onde o link aponta e roubaria o token.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from functools import cache

from py_vapid import Vapid

from app.comandos.gerar_chaves_vapid import publica_de

log = logging.getLogger(__name__)

REMETENTE_NOME = "Portal Capibaribe Prime"
_URL_BASE = re.compile(
    r"^(https://[A-Za-z0-9.-]+(:[0-9]{1,5})?|http://(localhost|127\.0\.0\.1)(:[0-9]{1,5})?)$"
)
_CONTATO = re.compile(r"^(mailto:[^@\s]+@[^@\s]+|https://\S+)$")


@dataclass(frozen=True)
class ConfigPush:
    chave_privada: str = field(repr=False)
    chave_publica: str
    contato: str


@dataclass(frozen=True)
class ConfigEmail:
    usuario: str
    senha_app: str = field(repr=False)
    host: str
    porta: int
    url_base: str
    remetente_nome: str = REMETENTE_NOME


def _ler(nome: str) -> str:
    return os.environ.get(nome, "").strip()


def url_base() -> str | None:
    """`PORTAL_URL_BASE` sem a barra do fim; `https://` (ou a máquina local em
    desenvolvimento), sem caminho nem consulta. Fora disso, `None`."""
    valor = _ler("PORTAL_URL_BASE").rstrip("/")
    return valor if _URL_BASE.match(valor) else None


def config_push() -> ConfigPush | None:
    return _config_push(_ler("PORTAL_VAPID_PRIVADA"), _ler("PORTAL_VAPID_CONTATO"))


@cache
def _config_push(privada: str, contato: str) -> ConfigPush | None:
    if not privada or not contato:
        if privada or contato:
            log.warning("push desligado: falta PORTAL_VAPID_PRIVADA ou PORTAL_VAPID_CONTATO")
        return None
    if not _CONTATO.match(contato):
        log.warning("push desligado: PORTAL_VAPID_CONTATO precisa ser mailto: ou https://")
        return None
    try:
        publica = publica_de(Vapid.from_string(privada).public_key)
    except Exception:  # noqa: BLE001 - qualquer formato errado desliga, sem mostrar a chave
        log.warning("push desligado: PORTAL_VAPID_PRIVADA não é uma chave VAPID válida")
        return None
    return ConfigPush(chave_privada=privada, chave_publica=publica, contato=contato)


def config_email() -> ConfigEmail | None:
    return _config_email(
        _ler("PORTAL_SMTP_USUARIO"),
        _ler("PORTAL_SMTP_SENHA_APP"),
        _ler("PORTAL_SMTP_HOST") or "smtp.gmail.com",
        _ler("PORTAL_SMTP_PORTA") or "465",
        url_base(),
    )


@cache
def _config_email(
    usuario: str, senha: str, host: str, porta: str, base: str | None
) -> ConfigEmail | None:
    if not (usuario and senha and base):
        if usuario or senha or _ler("PORTAL_URL_BASE"):
            log.warning(
                "e-mail desligado: falta PORTAL_SMTP_USUARIO, PORTAL_SMTP_SENHA_APP ou "
                "PORTAL_URL_BASE válida"
            )
        return None
    if not porta.isdigit() or not 0 < int(porta) < 65536:
        log.warning("e-mail desligado: PORTAL_SMTP_PORTA precisa ser um número de porta")
        return None
    return ConfigEmail(usuario=usuario, senha_app=senha, host=host, porta=int(porta), url_base=base)


def limpar_cache() -> None:
    """Para os testes: esquece as configurações já calculadas."""
    _config_push.cache_clear()
    _config_email.cache_clear()
