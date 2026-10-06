"""Épico B do M2 · Esqueci a senha (H-04). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.3. Espelho TypeScript:
`web/src/recuperacao/tipos.ts`. As regras de senha são as do primeiro acesso
(`app.esquemas.acesso`), para a mensagem ser a mesma nas duas telas.
"""

from pydantic import Field, field_validator

from app.esquemas.acesso import SenhaNova, SenhaRepetida, validar_login
from app.esquemas.comum import Entrada, Saida, UnidadeRef

# `secrets.token_urlsafe(32)` tem 43 caracteres; o limite só barra lixo grande.
LIMITE_TOKEN = 100
# H-04: a mesma resposta sempre, tenha a unidade e-mail ou não.
MSG_PEDIDO = (
    "Se houver e-mail cadastrado, enviamos um link. Se não chegou, fale com a administração."
)


class PedirRecuperacao(Entrada):
    """`POST /api/acesso/recuperacao`. A tela monta o login com bloco e apartamento."""

    login: str

    @field_validator("login")
    @classmethod
    def _login(cls, login: str) -> str:
        return validar_login(login)


class RecuperacaoPedida(Saida):
    """Resposta 202, idêntica para qualquer login válido (H-04)."""

    mensagem: str


class LinkDeRecuperacao(Entrada):
    """`POST /api/acesso/recuperacao/conferir`: o token que veio no link do e-mail."""

    token: str = Field(min_length=1, max_length=LIMITE_TOKEN)


class LinkValido(Saida):
    """O link vale: a tela mostra a placa da unidade antes de pedir a senha nova."""

    unidade: UnidadeRef


class RedefinirSenha(Entrada):
    """`POST /api/acesso/recuperacao/redefinir`."""

    token: str = Field(min_length=1, max_length=LIMITE_TOKEN)
    senha_nova: SenhaNova
    senha_nova_repetida: SenhaRepetida
