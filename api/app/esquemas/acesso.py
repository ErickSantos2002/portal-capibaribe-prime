"""Épico A · Acesso (spec do M1, seção 4.2). Pertence ao épico A.

Espelho TypeScript: `web/src/acesso/tipos.ts`.
"""

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field, ValidationInfo, field_validator

from app.esquemas.comum import Entrada, ErroResposta, Papel, Saida, UnidadeRef, sem_controle
from app.seguranca.senhas import SENHA_INICIAL

LIMITE_SENHA = 200
MINIMO_SENHA = 8
LIMITE_NOME = 100
LIMITE_EMAIL = 254
_LOGIN = re.compile(r"^[1-9][0-7][0-9]{2}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MSG_CELULAR = "Confira o celular: DDD e número, como (81) 9 1234-5678."


# --- regras reaproveitadas ---------------------------------------------------------------------


def validar_senha_nova(senha: str) -> str:
    sem_controle(senha)
    if len(senha) < MINIMO_SENHA:
        raise ValueError("A senha nova precisa ter pelo menos 8 letras ou números.")
    if len(senha) > LIMITE_SENHA:
        raise ValueError("A senha pode ter até 200 letras ou números.")
    if senha == SENHA_INICIAL:
        raise ValueError("Escolha uma senha diferente da inicial, que todo mundo conhece.")
    return senha


def validar_repetida(repetida: str, info: ValidationInfo) -> str:
    if "senha_nova" in info.data and repetida != info.data["senha_nova"]:
        raise ValueError("As duas senhas estão diferentes. Escreva a mesma nas duas.")
    return repetida


def validar_nome(nome: str) -> str:
    sem_controle(nome)
    nome = nome.strip()
    if not nome:
        raise ValueError("Escreva o nome de quem responde pela unidade.")
    if len(nome) > LIMITE_NOME:
        raise ValueError("O nome pode ter até 100 letras.")
    return nome


def validar_celular(celular: str) -> str:
    """Aceita com ou sem máscara; guarda só os dígitos (DDD + número, 10 ou 11)."""
    sem_controle(celular)
    digitos = re.sub(r"\D", "", celular)
    if not 10 <= len(digitos) <= 11 or digitos[0] == "0":
        raise ValueError(MSG_CELULAR)
    return digitos


def validar_email(email: str | None) -> str | None:
    email = sem_controle(email or "").strip().lower()
    if not email:
        return None
    if len(email) > LIMITE_EMAIL or not _EMAIL.match(email):
        raise ValueError("Confira o e-mail, ou deixe em branco.")
    return email


Nome = Annotated[str, AfterValidator(validar_nome)]
Celular = Annotated[str, AfterValidator(validar_celular)]
Email = Annotated[str | None, AfterValidator(validar_email)]
SenhaNova = Annotated[str, AfterValidator(validar_senha_nova)]
# Confere com o campo `senha_nova`, que precisa vir antes no modelo.
SenhaRepetida = Annotated[str, AfterValidator(validar_repetida)]


# --- requisições -------------------------------------------------------------------------------


class Entrar(Entrada):
    """`POST /api/acesso/entrar`. A tela monta o login a partir do bloco e do apartamento."""

    login: str
    senha: str = Field(max_length=LIMITE_SENHA)

    @field_validator("login")
    @classmethod
    def _login(cls, login: str) -> str:
        if not _LOGIN.match(login):
            raise ValueError("Escolha o bloco e escreva o número do apartamento.")
        return login

    @field_validator("senha")
    @classmethod
    def _senha(cls, senha: str) -> str:
        if not senha:
            raise ValueError("Escreva a senha.")
        return senha


class Contato(Entrada):
    """Responsável, celular e e-mail opcional (RF-04, RNF-10)."""

    responsavel_nome: Nome
    celular: Celular
    email: Email = None


class PrimeiroAcesso(Contato):
    """`POST /api/acesso/primeiro-acesso` (H-01)."""

    senha_nova: SenhaNova
    senha_nova_repetida: SenhaRepetida


class DadosDaUnidade(Contato):
    """`PUT /api/minha-unidade/dados` (H-06)."""


class TrocarSenha(Entrada):
    """`PUT /api/minha-unidade/senha` (H-06)."""

    senha_atual: str = Field(max_length=LIMITE_SENHA)
    senha_nova: SenhaNova
    senha_nova_repetida: SenhaRepetida


class ApagarDados(Entrada):
    """`POST /api/minha-unidade/apagar-dados`: `{"confirmo": true}` (H-06)."""

    confirmo: bool

    @field_validator("confirmo")
    @classmethod
    def _confirmo(cls, confirmo: bool) -> bool:
        if confirmo is not True:
            raise ValueError("Confirme que quer apagar os dados.")
        return confirmo


# --- respostas ---------------------------------------------------------------------------------


class Aparelho(Saida):
    id: int
    descricao: str
    criada_em: datetime
    ultimo_uso_em: datetime
    este_aparelho: bool


class MinhaUnidade(Saida):
    """`GET /api/minha-unidade` (H-06)."""

    unidade: UnidadeRef
    responsavel_nome: str | None
    celular: str | None
    email: str | None
    papeis: list[Papel]
    ativada_em: datetime | None
    aparelhos: list[Aparelho]


class ErroBloqueio(ErroResposta):
    """423 `unidade_bloqueada` de `POST /api/acesso/entrar` (H-03)."""

    bloqueada_ate: datetime
    minutos_restantes: int
