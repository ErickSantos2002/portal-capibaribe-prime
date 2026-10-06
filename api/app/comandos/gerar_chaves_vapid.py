"""Gera um par de chaves VAPID para o Web Push (ADR-0006). Uso, de `api/`:

    uv run python -m app.comandos.gerar_chaves_vapid

Imprime a linha `PORTAL_VAPID_PRIVADA=...` para colar nas variáveis de ambiente da Vercel
(Production; a prévia usa outro par) e a chave pública só para conferência: a API calcula a
pública a partir da privada. **Nunca grave a saída no repositório.** Trocar o par depois faz
todos os aparelhos precisarem ativar as notificações de novo.
"""

import base64
import sys
from dataclasses import dataclass, field

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


@dataclass(frozen=True)
class ParVapid:
    privada: str = field(repr=False)
    publica: str


def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def publica_de(chave: ec.EllipticCurvePublicKey) -> str:
    """A chave pública no formato que o navegador pede (`applicationServerKey`): o ponto P-256
    não comprimido (65 bytes), em base64url sem `=`."""
    return _b64url(
        chave.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
    )


def gerar() -> ParVapid:
    """Par novo. A privada vai como os 32 bytes crus em base64url (formato que o `py_vapid`
    lê)."""
    chave = ec.generate_private_key(ec.SECP256R1())
    privada = _b64url(chave.private_numbers().private_value.to_bytes(32, "big"))
    return ParVapid(privada=privada, publica=publica_de(chave.public_key()))


def main() -> int:
    par = gerar()
    print("# Cole na Vercel (variável sensível). Não grave no repositório.")
    print(f"PORTAL_VAPID_PRIVADA={par.privada}")
    print(f"# Pública (a API calcula sozinha; só para conferir): {par.publica}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
