"""Notificações e recuperação de senha (M2, migração 0005): `inscricao_push`,
`token_recuperacao`, `notificacao_envio`. Spec: `docs/superpowers/specs/m2-contrato.md`.

Regras que o banco garante e que estes modelos não repetem: datas carimbadas pelo banco; a
inscrição some quando a sessão é encerrada e no máximo 10 por unidade; o token vale 1 hora, uma
vez só, só para unidade ativada com e-mail, até 3 por hora e 6 por dia por unidade; o envio
nasce pendente e a situação só anda para a frente.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    FetchedValue,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria

LIMITE_INSCRICOES_POR_UNIDADE = 10
VALIDADE_TOKEN_HORAS = 1
TOKENS_POR_HORA = 3
TOKENS_POR_DIA = 6


class Canal(enum.StrEnum):
    push = "push"
    email = "email"


class SituacaoEnvio(enum.StrEnum):
    pendente = "pendente"
    enviando = "enviando"
    concluido = "concluido"
    desligado = "desligado"
    interrompido = "interrompido"


class InscricaoPush(Base):
    """Para onde mandar o push de um aparelho (uma por sessão)."""

    __tablename__ = "inscricao_push"
    __table_args__ = (
        CheckConstraint(
            "endpoint ~ '^https://' and char_length(endpoint) <= 2048",
            name="inscricao_push_endpoint",
        ),
        CheckConstraint("chave_p256dh ~ '^[A-Za-z0-9_-]{87}=?$'", name="inscricao_push_p256dh"),
        CheckConstraint("chave_auth ~ '^[A-Za-z0-9_-]{22}(==)?$'", name="inscricao_push_auth"),
    )

    sessao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sessao.id", ondelete="CASCADE"), primary_key=True
    )
    endpoint: Mapped[str] = mapped_column(unique=True)
    chave_p256dh: Mapped[str]
    chave_auth: Mapped[str]
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())


class TokenRecuperacao(Base):
    """Link de "esqueci a senha" (H-04). Só o SHA-256 do token."""

    __tablename__ = "token_recuperacao"
    __table_args__ = (
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_recuperacao_hash"),
        Index("token_recuperacao_unidade", "unidade_id", "criado_em"),
    )

    id: Mapped[int] = chave_primaria()
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    # O banco calcula (criação + 1 hora) e ignora o que vier da aplicação.
    expira_em: Mapped[datetime] = mapped_column(server_default=FetchedValue())
    usado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())


class NotificacaoEnvio(Base):
    """Um envio por aviso e canal: impede mandar duas vezes e mede a entrega (só contagens)."""

    __tablename__ = "notificacao_envio"
    __table_args__ = (
        UniqueConstraint("aviso_id", "canal", name="notificacao_envio_unico"),
        CheckConstraint("canal in ('push', 'email')", name="notificacao_envio_canal"),
        CheckConstraint(
            "situacao in ('pendente', 'enviando', 'concluido', 'desligado', 'interrompido')",
            name="notificacao_envio_situacao_valor",
        ),
        CheckConstraint(
            "destinos >= 0 and entregues >= 0 and falhas >= 0 and removidas >= 0"
            " and pulados >= 0 and entregues + falhas + pulados <= destinos"
            " and removidas <= falhas",
            name="notificacao_envio_contagens",
        ),
        Index(
            "notificacao_envio_em_aberto",
            "criado_em",
            postgresql_where=text("situacao in ('pendente', 'enviando')"),
        ),
    )

    id: Mapped[int] = chave_primaria()
    aviso_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aviso.id"))
    canal: Mapped[str]
    situacao: Mapped[str] = mapped_column(server_default="pendente")
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    iniciado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    concluido_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    destinos: Mapped[int] = mapped_column(server_default="0")
    entregues: Mapped[int] = mapped_column(server_default="0")
    falhas: Mapped[int] = mapped_column(server_default="0")
    removidas: Mapped[int] = mapped_column(server_default="0")
    pulados: Mapped[int] = mapped_column(server_default="0")
