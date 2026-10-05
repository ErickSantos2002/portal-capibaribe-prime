"""Unidades e acesso: `bloco`, `unidade`, `unidade_papel`, `sessao` (modelo, seção 3.1)."""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    FetchedValue,
    ForeignKey,
    Index,
    SmallInteger,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria


class Papel(enum.StrEnum):
    admin = "admin"
    comissao = "comissao"
    sindico = "sindico"
    conselho = "conselho"


class Bloco(Base):
    __tablename__ = "bloco"

    id: Mapped[int] = chave_primaria()
    numero: Mapped[int] = mapped_column(SmallInteger, unique=True)
    nome: Mapped[str]
    ativo: Mapped[bool] = mapped_column(server_default="true")


class Unidade(Base):
    """Um apartamento e a conta de acesso dele (uma conta por unidade, ADR-0005)."""

    __tablename__ = "unidade"
    __table_args__ = (
        UniqueConstraint("bloco_id", "numero"),
        # Migração 0002 (RF-04): os contatos são obrigatórios depois de ativar, e cada um tem
        # formato único. O celular é guardado só com dígitos; a tela formata.
        CheckConstraint(
            "ativada_em is null or (responsavel_nome is not null and celular is not null)",
            name="unidade_ativada_tem_contato",
        ),
        CheckConstraint(
            "responsavel_nome is null or (char_length(responsavel_nome) between 1 and 100"
            " and responsavel_nome = btrim(responsavel_nome))",
            name="unidade_nome_formato",
        ),
        CheckConstraint(
            "celular is null or celular ~ '^[0-9]{10,11}$'", name="unidade_celular_formato"
        ),
        CheckConstraint(
            "email is null or (char_length(email) <= 254 and email = lower(email))",
            name="unidade_email_formato",
        ),
    )

    id: Mapped[int] = chave_primaria()
    bloco_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bloco.id"))
    numero: Mapped[str]
    andar: Mapped[int] = mapped_column(SmallInteger)
    # Gerado pelo banco (trigger): bloco.numero + numero, ex.: '1101'.
    login: Mapped[str] = mapped_column(
        unique=True, server_default=FetchedValue(), server_onupdate=FetchedValue()
    )
    ativa: Mapped[bool] = mapped_column(server_default="true")
    senha_hash: Mapped[str]
    precisa_trocar_senha: Mapped[bool] = mapped_column(server_default="true")
    ativada_em: Mapped[datetime | None]
    # Dados pessoais (modelo, seção 5): só depois do primeiro acesso.
    responsavel_nome: Mapped[str | None]
    celular: Mapped[str | None]
    email: Mapped[str | None]
    tentativas_falhas: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    bloqueada_ate: Mapped[datetime | None]


class UnidadePapel(Base):
    """Papel de gestão. Retirar preenche `retirado_em`; a linha nunca é apagada.

    Banco (migração 0002): datas carimbadas com now(); o `app` só altera `retirado_em` e
    `retirado_por`; papel retirado não volta; o último `admin` não pode ser retirado (falha com
    a restrição `ultimo_admin`).
    """

    __tablename__ = "unidade_papel"
    # Um papel em vigor por tipo por unidade.
    __table_args__ = (
        Index(
            "unidade_papel_em_vigor",
            "unidade_id",
            "papel",
            unique=True,
            postgresql_where=text("retirado_em is null"),
        ),
    )

    id: Mapped[int] = chave_primaria()
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    papel: Mapped[Papel] = mapped_column(Enum(Papel, name="papel"))
    concedido_em: Mapped[datetime] = mapped_column(server_default=func.now())
    concedido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    retirado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    retirado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))


class Sessao(Base):
    """Cada aparelho conectado. O banco guarda só o hash do token."""

    __tablename__ = "sessao"
    __table_args__ = (Index("sessao_unidade", "unidade_id"),)

    id: Mapped[int] = chave_primaria()
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    aparelho: Mapped[str | None]
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())
    ultimo_uso_em: Mapped[datetime] = mapped_column(server_default=func.now())
    encerrada_em: Mapped[datetime | None]
