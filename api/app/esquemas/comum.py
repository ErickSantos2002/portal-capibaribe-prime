"""Esquemas comuns a todos os épicos (spec do M1, seções 3.4 e 4.1).

Cada esquema tem um espelho em TypeScript (`web/src/api/tipos.ts` para estes); o teste
`testes/test_contrato.py` confere que os campos batem.
"""

from pydantic import BaseModel, ConfigDict

from app.modelos import Papel

__all__ = ["CampoInvalido", "Entrada", "ErroResposta", "Eu", "Papel", "Saida", "UnidadeRef"]


class Entrada(BaseModel):
    """Base dos corpos de requisição: campo desconhecido é erro (pega front desatualizado)."""

    model_config = ConfigDict(extra="forbid")


class Saida(BaseModel):
    """Base das respostas."""


class UnidadeRef(Saida):
    """Como a unidade aparece em toda resposta: `{"login": "1101", "bloco": 1, "apartamento":
    "101"}`. A tela mostra "Bloco 1, 101", nunca o código colado."""

    login: str
    bloco: int
    apartamento: str

    @classmethod
    def de_login(cls, login: str) -> "UnidadeRef":
        return cls(login=login, bloco=int(login[0]), apartamento=login[1:])


class Eu(Saida):
    """`GET /api/acesso/eu`: o que a casca do front precisa para escolher rotas e menu."""

    unidade: UnidadeRef
    papeis: list[Papel]
    gestao: bool
    admin: bool
    precisa_trocar_senha: bool


class CampoInvalido(Saida):
    campo: str | None
    mensagem: str


class ErroResposta(Saida):
    """Corpo de todo erro previsto. Erros de validação (422) trazem também `campos`; alguns
    trazem extras documentados na rota (ex.: `bloqueada_ate`)."""

    codigo: str
    mensagem: str
    campos: list[CampoInvalido] | None = None
