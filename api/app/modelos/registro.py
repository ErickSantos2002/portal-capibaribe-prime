"""Registros: `historico` (só inclusão) e `erro` (exceções da API). Modelo, seção 3.6."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria


class Historico(Base):
    """O usuário `app` só insere aqui: sem UPDATE e sem DELETE (garantido pelo banco)."""

    __tablename__ = "historico"
    __table_args__ = (Index("historico_ocorrido_em", "ocorrido_em"),)

    id: Mapped[int] = chave_primaria()
    ocorrido_em: Mapped[datetime] = mapped_column(server_default=func.now())
    # Nulo = o próprio sistema (ex.: carga inicial, bloqueio automático).
    unidade_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    acao: Mapped[str]
    entidade: Mapped[str | None]
    entidade_id: Mapped[int | None] = mapped_column(BigInteger)
    # Contexto, sem dado pessoal e sem senha.
    detalhes: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")


class Erro(Base):
    """Exceção não tratada da API (os logs grátis da Vercel duram 1 hora)."""

    __tablename__ = "erro"
    __table_args__ = (Index("erro_ocorrido_em", "ocorrido_em"),)

    id: Mapped[int] = chave_primaria()
    ocorrido_em: Mapped[datetime] = mapped_column(server_default=func.now())
    rota: Mapped[str]
    tipo: Mapped[str]
    mensagem: Mapped[str]
    unidade_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
