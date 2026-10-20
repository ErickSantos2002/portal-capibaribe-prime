"""Classificados entre vizinhos (migração 0011): `categoria_classificado`, `anuncio`,
`anuncio_foto`, `aviso_anuncio`. Spec: `docs/superpowers/specs/2026-10-20-classificados-design.md`,
seções 4 a 6; as fotos: ADR-0012.

Regras que o banco garante e que estes modelos não repetem: datas carimbadas pelo banco (inclusive
`vence_em`, 30 dias depois de publicar ou renovar); só unidade **ativa** anuncia, envia foto e
avisa; situação `ativo` ↔ `reservado` → `encerrado`, e encerrado não muda; vencido só renova ou
encerra; renovar só a menos de 7 dias de vencer; escondido só encerra; 5 anúncios novos por dia e
10 abertos por unidade; até 4 fotos por anúncio, da mesma unidade; 40 fotos enviadas por unidade
a cada 24 horas; um aviso aberto por unidade e anúncio, 10 por dia; anúncio com foto presa não é
apagado; o `app` não apaga categoria.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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

# Nome e ordem da carga inicial (spec, seção 4). A migração 0011 grava esta mesma lista.
ORDEM_OUTROS = 999
CATEGORIAS_INICIAIS: tuple[tuple[str, int], ...] = (
    ("Móveis", 10),
    ("Eletrodomésticos", 20),
    ("Eletrônicos", 30),
    ("Material de obra e acabamento", 40),
    ("Decoração", 50),
    ("Utilidades domésticas", 60),
    ("Infantil", 70),
    ("Outros", ORDEM_OUTROS),
)
MIN_TITULO = 3
LIMITE_TITULO = 80
LIMITE_DESCRICAO = 1000
LIMITE_MOTIVO = 300
LIMITE_CATEGORIA = 40
# R$ 100.000, em centavos.
PRECO_MAXIMO = 10_000_000
FOTOS_POR_ANUNCIO = 4
MB = 1024 * 1024
LIMITE_FOTO = 10 * MB
# Por unidade (spec, seção 4; as fotos: ADR-0012).
ANUNCIOS_POR_DIA = 5
ANUNCIOS_ABERTOS = 10
FOTOS_POR_DIA = 40
AVISOS_POR_DIA = 10
DIAS_PARA_VENCER = 30
DIAS_PARA_RENOVAR = 7
# Faxina (spec, seção 6): vencido há mais de 30 dias, encerrado há mais de 7.
FAXINA_VENCIDO_DIAS = 30
FAXINA_ENCERRADO_DIAS = 7
TIPOS_DE_FOTO = ("image/jpeg", "image/png", "image/webp")


class TipoAnuncio(enum.StrEnum):
    venda = "venda"
    troca = "troca"
    doacao = "doacao"


class SituacaoAnuncio(enum.StrEnum):
    ativo = "ativo"
    reservado = "reservado"
    encerrado = "encerrado"


class MotivoEncerramento(enum.StrEnum):
    vendi = "vendi"
    troquei = "troquei"
    doei = "doei"
    desisti = "desisti"


def _lista(valores) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _texto_opcional(coluna: str, limite: int) -> str:
    return (
        f"{coluna} is null or (char_length(btrim({coluna})) between 1 and {limite}"
        f" and char_length({coluna}) <= {limite})"
    )


class CategoriaClassificado(Base):
    __tablename__ = "categoria_classificado"
    __table_args__ = (
        CheckConstraint(
            f"char_length(nome) between 2 and {LIMITE_CATEGORIA} and nome = btrim(nome)",
            name="categoria_classificado_nome_tamanho",
        ),
        Index("categoria_classificado_nome_unico", func.lower(text("nome")), unique=True),
    )

    id: Mapped[int] = chave_primaria()
    nome: Mapped[str]
    ordem: Mapped[int] = mapped_column(SmallInteger)
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())


class Anuncio(Base):
    """O anúncio da unidade. Some com a faxina, "apagar meus dados" e o reset."""

    __tablename__ = "anuncio"
    __table_args__ = (
        CheckConstraint(f"tipo in ({_lista(TipoAnuncio)})", name="anuncio_tipo"),
        CheckConstraint(
            f"char_length(titulo) between {MIN_TITULO} and {LIMITE_TITULO}"
            " and titulo = btrim(titulo)",
            name="anuncio_titulo_tamanho",
        ),
        CheckConstraint(
            _texto_opcional("descricao", LIMITE_DESCRICAO), name="anuncio_descricao_tamanho"
        ),
        CheckConstraint(
            "preco_centavos is null"
            f" or (tipo = 'venda' and preco_centavos between 0 and {PRECO_MAXIMO})",
            name="anuncio_preco",
        ),
        CheckConstraint(
            "contato ~ '^[1-9]{2}(9[0-9]{8}|[2-5][0-9]{7})$'", name="anuncio_contato_formato"
        ),
        CheckConstraint(f"situacao in ({_lista(SituacaoAnuncio)})", name="anuncio_situacao"),
        CheckConstraint(
            f"motivo_encerramento in ({_lista(MotivoEncerramento)})",
            name="anuncio_motivo_encerramento",
        ),
        CheckConstraint(
            "(situacao = 'encerrado') = (motivo_encerramento is not null)"
            " and (situacao = 'encerrado') = (encerrado_em is not null)",
            name="anuncio_encerramento",
        ),
        Index("anuncio_unidade", "unidade_id", "publicado_em"),
        Index("anuncio_vence", "vence_em"),
    )

    id: Mapped[int] = chave_primaria()
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categoria_classificado.id"))
    tipo: Mapped[str]
    titulo: Mapped[str]
    descricao: Mapped[str | None]
    # Só na venda; nulo = "a combinar".
    preco_centavos: Mapped[int | None]
    # Só os dígitos, com DDD e sem o 55.
    contato: Mapped[str]
    situacao: Mapped[str] = mapped_column(server_default=text("'ativo'"))
    motivo_encerramento: Mapped[str | None]
    publicado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    renovado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    vence_em: Mapped[datetime] = mapped_column(
        server_default=text("now() + interval '30 days'"), server_onupdate=FetchedValue()
    )
    editado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    encerrado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondido_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))


class AnuncioFoto(Base):
    """A foto do anúncio, em `classificados/<chave>` (ADR-0012): pendente, pronta, no anúncio
    (com `ordem`, a 0 é a capa) ou descartada."""

    __tablename__ = "anuncio_foto"
    __table_args__ = (
        UniqueConstraint("chave", name="anuncio_foto_chave_unica"),
        CheckConstraint("chave ~ '^[0-9a-f]{32}$'", name="anuncio_foto_chave"),
        CheckConstraint(f"tipo in ({_lista(TIPOS_DE_FOTO)})", name="anuncio_foto_tipo"),
        CheckConstraint(f"bytes between 1 and {LIMITE_FOTO}", name="anuncio_foto_bytes"),
        CheckConstraint(f"ordem between 0 and {FOTOS_POR_ANUNCIO - 1}", name="anuncio_foto_ordem"),
        CheckConstraint(
            "(anuncio_id is null) = (ordem is null)"
            " and (anuncio_id is null or (confirmada_em is not null and descartada_em is null))",
            name="anuncio_foto_estado",
        ),
        Index("anuncio_foto_anuncio", "anuncio_id"),
        Index("anuncio_foto_unidade", "unidade_id", "enviada_em"),
    )

    id: Mapped[int] = chave_primaria()
    anuncio_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("anuncio.id"))
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    chave: Mapped[str]
    tipo: Mapped[str]
    bytes: Mapped[int]
    ordem: Mapped[int | None] = mapped_column(SmallInteger)
    enviada_em: Mapped[datetime] = mapped_column(server_default=func.now())
    confirmada_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    descartada_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())


class AvisoAnuncio(Base):
    """ "Tem algo errado aqui?": um aberto por unidade e anúncio. Só a gestão vê."""

    __tablename__ = "aviso_anuncio"
    __table_args__ = (
        CheckConstraint(
            _texto_opcional("motivo", LIMITE_MOTIVO), name="aviso_anuncio_motivo_tamanho"
        ),
        Index(
            "aviso_anuncio_aberto",
            "anuncio_id",
            "unidade_id",
            unique=True,
            postgresql_where=text("resolvido_em is null"),
        ),
        Index("aviso_anuncio_unidade", "unidade_id", "criado_em"),
    )

    id: Mapped[int] = chave_primaria()
    anuncio_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.id", ondelete="CASCADE")
    )
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    motivo: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    resolvido_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    resolvido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
