"""Esquemas comuns a todos os épicos (spec do M1, seções 3.4 e 4.1).

Cada esquema tem um espelho em TypeScript (`web/src/api/tipos.ts` para estes); o teste
`testes/test_contrato.py` confere que os campos batem.
"""

import unicodedata
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modelos import Canal, Papel, SituacaoEnvio

__all__ = [
    "MSG_CONTROLE",
    "CampoInvalido",
    "Canal",
    "EnvioDoAviso",
    "EnviosDoAviso",
    "Entrada",
    "ErroResposta",
    "Eu",
    "Papel",
    "SituacaoEnvio",
    "Saida",
    "UnidadeRef",
    "sem_controle",
]

MSG_CONTROLE = "Tem um caractere invisível no texto. Apague e escreva de novo."


def sem_controle(texto: str, *, permitidos: str = "") -> str:
    """Recusa NUL e caracteres de controle (Unicode `Cc`: C0, DEL e C1) em texto livre
    (revisão do M1, C3). O Postgres não guarda `\\x00` em `text` e isso virava erro 500; os
    outros não têm uso em nome, título ou busca. `permitidos`: os que o campo aceita (o texto
    do aviso aceita `\\n` e `\\t`)."""
    for caractere in texto:
        if unicodedata.category(caractere) == "Cc" and caractere not in permitidos:
            raise ValueError(MSG_CONTROLE)
    return texto


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


class EnvioDoAviso(Saida):
    """Como foi a notificação de um aviso num canal (spec do M2, seção 4.4). Só contagens:
    `destinos` são aparelhos (push) ou unidades (e-mail); `pulados`, e-mails que não couberam na
    cota do dia; `removidas`, aparelhos que o serviço de push disse não existir mais."""

    canal: Canal
    situacao: SituacaoEnvio
    destinos: int
    entregues: int
    falhas: int
    removidas: int
    pulados: int
    criado_em: datetime
    concluido_em: datetime | None


class EnviosDoAviso(Saida):
    """`GET /api/avisos/{id}/envios` (gestão). Vazio para aviso publicado antes do M2."""

    itens: list[EnvioDoAviso]
