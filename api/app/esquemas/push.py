"""Épico A do M2 · Notificações no aparelho (H-05, H-13). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.2. Espelho TypeScript:
`web/src/notificacoes/tipos.ts`.
"""

import re
from urllib.parse import urlsplit

from pydantic import field_validator
from urllib3.util import parse_url

from app.esquemas.avisos import Categoria
from app.esquemas.comum import Entrada, Saida

LIMITE_ENDPOINT = 2048
# Serviços de push dos navegadores (Chrome, Samsung, Opera e Edge Android usam o do Google).
# A API faz um POST para o endpoint que o aparelho manda: sem esta lista, uma conta qualquer
# faria a função da Vercel chamar endereços escolhidos por ela (SSRF).
SERVICOS_DE_PUSH = (
    "fcm.googleapis.com",  # Chrome, Android
    "push.services.mozilla.com",  # Firefox (updates.push.services.mozilla.com)
    "push.apple.com",  # Safari no iPhone e no Mac (web.push.apple.com)
    "notify.windows.com",  # Edge no Windows (wns2-*.notify.windows.com)
)
MSG_ENDPOINT = "Este navegador mandou um endereço de notificação que o Portal não reconhece."
MSG_CHAVE = "Este navegador mandou uma chave de notificação fora do padrão."
_P256DH = re.compile(r"^[A-Za-z0-9_-]{87}=?$")
_AUTH = re.compile(r"^[A-Za-z0-9_-]{22}(==)?$")


# Só o que um serviço de push manda de verdade: https, host só com letras, números, ponto e
# hífen, e caminho com caracteres visíveis de URL, **sem barra invertida**. Revisão do épico
# A: o `urlsplit` e o urllib3 (que o `requests` usa no envio) leem `\\` de jeitos diferentes,
# e `https://169.254.169.254\\.fcm.googleapis.com/` conectava no 169.254.169.254. Sem porta,
# sem usuário, sem `%`, espaço ou `@` no host.
_FORMATO_ENDPOINT = re.compile(r"https://[A-Za-z0-9.-]+(/[!-\[\]-~]*)?")


def servico_de_push_conhecido(endpoint: str) -> bool:
    """O endpoint é de um serviço de push da lista, lido **pelo mesmo parser do envio**
    (urllib3) e pelo `urlsplit`; os dois precisam concordar."""
    if not _FORMATO_ENDPOINT.fullmatch(endpoint):
        return False
    try:
        partes = urlsplit(endpoint)
        porta = partes.port
        envio = parse_url(endpoint)
    except ValueError:
        return False
    host = partes.hostname or ""
    return (
        partes.scheme == "https"
        and porta is None
        and partes.username is None
        and partes.password is None
        and envio.scheme == "https"
        and envio.host == host
        and envio.port is None
        and envio.auth is None
        and not host.endswith(".")
        and any(host == s or host.endswith("." + s) for s in SERVICOS_DE_PUSH)
    )


class InscricaoPush(Entrada):
    """`PUT /api/notificacoes/este-aparelho`: o `PushSubscription.toJSON()` do navegador,
    achatado (`keys.p256dh` → `p256dh`, `keys.auth` → `auth`)."""

    endpoint: str
    p256dh: str
    auth: str

    @field_validator("endpoint")
    @classmethod
    def _endpoint(cls, endpoint: str) -> str:
        if len(endpoint) > LIMITE_ENDPOINT or not servico_de_push_conhecido(endpoint):
            raise ValueError(MSG_ENDPOINT)
        return endpoint

    @field_validator("p256dh")
    @classmethod
    def _p256dh(cls, chave: str) -> str:
        if not _P256DH.match(chave):
            raise ValueError(MSG_CHAVE)
        return chave

    @field_validator("auth")
    @classmethod
    def _auth(cls, chave: str) -> str:
        if not _AUTH.match(chave):
            raise ValueError(MSG_CHAVE)
        return chave


class EstadoNotificacoes(Saida):
    """`GET /api/notificacoes`: o que a tela precisa para oferecer "Ativar notificações".

    `disponivel` falso (sem chaves VAPID no servidor) esconde a oferta; `chave_publica` é o
    `applicationServerKey` do `pushManager.subscribe`; `este_aparelho` diz se a sessão deste
    aparelho tem inscrição guardada.
    """

    disponivel: bool
    chave_publica: str | None
    este_aparelho: bool


class PushAviso(Saida):
    """Corpo (JSON, cifrado pelo Web Push) da notificação de aviso, lido pelo service worker.
    O SW mostra `titulo` e abre `url` (`/avisos/<id>`) no toque (H-13)."""

    aviso_id: int
    titulo: str
    categoria: Categoria
    url: str
