"""IP de quem fez a requisição, e o hash que vai para o banco (bloqueio por tentativas, H-03).

**De onde vem o IP.** Na Vercel, de `x-real-ip`. A documentação da Vercel ("Request headers",
https://vercel.com/docs/headers/request-headers, conferida em 05/10/2026) diz que `x-real-ip` "é
idêntico ao `x-forwarded-for`" e que a Vercel **sobrescreve** o `x-forwarded-for` e não repassa
IPs externos, "para impedir falsificação de IP". Fora da Vercel (local, testes), o cabeçalho
viria do próprio cliente e seria falsificável: vale o endereço da conexão
(`request.client.host`). A Vercel se identifica pela variável de sistema `VERCEL=1`.

**O que vai para o banco.** Só `HMAC-SHA256(chave, ip)` em hexadecimal, nunca o IP cru (LGPD:
o IP é dado pessoal e o bloqueio não precisa dele, só de reconhecer o mesmo endereço de novo).
HMAC, e não hash simples, porque há só 4 bilhões de IPv4: sem chave, um hash vazado se desfaz
por força bruta em minutos. A chave sai da `DATABASE_URL` (que tem a senha do usuário `app` e
já é segredo em todo ambiente): não há variável nova para configurar. Se a senha do banco mudar,
os hashes mudam, o que só zera contadores que expiram em 15 minutos de qualquer jeito.
"""

import hashlib
import hmac
import os

from starlette.requests import Request

DESCONHECIDO = "desconhecido"


def ip_do_cliente(request: Request) -> str:
    if os.environ.get("VERCEL") == "1":
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real
    return request.client.host if request.client else DESCONHECIDO


def _chave() -> bytes:
    url = os.environ.get("DATABASE_URL", "")
    return hashlib.sha256(b"portal:ip:" + url.encode()).digest()


def hash_do_ip(ip: str) -> str:
    return hmac.new(_chave(), ip.encode(), hashlib.sha256).hexdigest()
