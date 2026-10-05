"""Avisos sem anexo: `aviso`, `aviso_versao`, `aviso_bloco`, `aviso_leitura` (modelo, seção 3.3).

Regras que o banco garante (migração 0002) e que estes modelos não repetem: datas carimbadas
pelo banco, versões em sequência, aviso completo no commit (versão 1 e destino), o `app` sem
DELETE em nada daqui e só podendo alterar `aviso.fixado` e `aviso.arquivado_em`.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    FetchedValue,
    ForeignKey,
    Index,
    SmallInteger,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.acesso import Papel
from app.modelos.base import Base, chave_primaria

LIMITE_TITULO = 120
LIMITE_TEXTO = 10_000


class Aviso(Base):
    __tablename__ = "aviso"
    __table_args__ = (Index("aviso_publicado_em", "publicado_em"),)

    id: Mapped[int] = chave_primaria()
    publicado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    # Assinatura do aviso ("Publicado pela Comissão"), congelada na publicação.
    publicado_como: Mapped[Papel] = mapped_column(Enum(Papel, name="papel", create_type=False))
    publicado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    para_todos: Mapped[bool]
    fixado: Mapped[bool] = mapped_column(server_default="false")
    # Carimbado pelo banco ao arquivar (qualquer valor não nulo vira now()).
    arquivado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())


class AvisoVersao(Base):
    """Título e texto. A versão 1 é a publicação; correção é versão nova, nunca UPDATE."""

    __tablename__ = "aviso_versao"
    __table_args__ = (
        CheckConstraint("versao >= 1"),
        CheckConstraint(
            f"char_length(btrim(titulo)) between 1 and {LIMITE_TITULO}"
            f" and char_length(titulo) <= {LIMITE_TITULO}"
        ),
        CheckConstraint(
            f"char_length(btrim(texto)) between 1 and {LIMITE_TEXTO}"
            f" and char_length(texto) <= {LIMITE_TEXTO}"
        ),
    )

    aviso_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aviso.id"), primary_key=True)
    versao: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    titulo: Mapped[str]
    texto: Mapped[str]
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())
    criada_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))


class AvisoBloco(Base):
    """Destino quando `aviso.para_todos` é falso."""

    __tablename__ = "aviso_bloco"
    __table_args__ = (Index("aviso_bloco_bloco", "bloco_id"),)

    aviso_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aviso.id"), primary_key=True)
    bloco_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bloco.id"), primary_key=True)


class AvisoLeitura(Base):
    """Primeira abertura do aviso pela unidade (H-16). Gravar com `on conflict do nothing`."""

    __tablename__ = "aviso_leitura"
    __table_args__ = (Index("aviso_leitura_unidade", "unidade_id"),)

    aviso_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aviso.id"), primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"), primary_key=True)
    lido_em: Mapped[datetime] = mapped_column(server_default=func.now())
