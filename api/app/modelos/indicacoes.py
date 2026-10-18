"""Indicações de serviços (migração 0010): `categoria_servico`, `prestador`, `opiniao_servico`,
`aviso_servico`. Spec: `docs/superpowers/specs/2026-10-18-indicacoes-design.md`, seções 4 e 5.

Regras que o banco garante e que estes modelos não repetem: datas carimbadas pelo banco; só
unidade **ativa** indica, opina e avisa; **uma opinião por unidade e prestador**; telefone único
entre todos os prestadores, escondidos inclusive; até 10 indicações e 30 opiniões novas por
unidade a cada 24 horas (as opiniões apagadas pela própria unidade contam, pelo histórico);
prestador escondido não muda nem recebe opinião ou aviso; opinião escondida fica travada;
`criado_por` só vira nulo; um aviso aberto por unidade e prestador; o `app` não apaga prestador
nem categoria.

Gravar a opinião sempre com `select … for update` e depois `UPDATE` ou `INSERT`, nunca com
`insert … on conflict`: o `BEFORE INSERT` contaria a mudança no limite do dia.
"""

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

# Nome e ordem da carga inicial (spec, seção 4). A migração 0010 grava esta mesma lista (o
# teste `test_carga_da_migracao_igual_a_constante` confere). "Outros" fica sempre por último.
ORDEM_OUTROS = 999
CATEGORIAS_INICIAIS: tuple[tuple[str, int], ...] = (
    ("Móveis planejados", 10),
    ("Ar-condicionado", 20),
    ("Cortinas e persianas", 30),
    ("Mudança", 40),
    ("Eletricista", 50),
    ("Encanador", 60),
    ("Pintura", 70),
    ("Gesso", 80),
    ("Vidraçaria e box", 90),
    ("Diarista", 100),
    ("Outros", ORDEM_OUTROS),
)
MIN_NOME = 2
LIMITE_NOME = 80
LIMITE_COMENTARIO = 500
LIMITE_MOTIVO = 300
LIMITE_CATEGORIA = 40
LIMITE_INSTAGRAM = 30
# Por unidade, a cada 24 horas (spec, seção 4).
INDICACOES_POR_DIA = 10
OPINIOES_POR_DIA = 30


def _texto_opcional(coluna: str, limite: int) -> str:
    """Nulo, ou de 1 a `limite` letras sem contar os espaços das pontas."""
    return (
        f"{coluna} is null or (char_length(btrim({coluna})) between 1 and {limite}"
        f" and char_length({coluna}) <= {limite})"
    )


class CategoriaServico(Base):
    """Fixas, com carga inicial. A administração acrescenta e renomeia; nunca apaga."""

    __tablename__ = "categoria_servico"
    __table_args__ = (
        CheckConstraint(
            f"char_length(nome) between {MIN_NOME} and {LIMITE_CATEGORIA} and nome = btrim(nome)",
            name="categoria_servico_nome_tamanho",
        ),
        Index("categoria_servico_nome_unico", func.lower(text("nome")), unique=True),
    )

    id: Mapped[int] = chave_primaria()
    nome: Mapped[str]
    ordem: Mapped[int] = mapped_column(SmallInteger)
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())


class Prestador(Base):
    """Quem foi indicado. Nasce com a primeira opinião; escondido, sai da lista para sempre."""

    __tablename__ = "prestador"
    __table_args__ = (
        UniqueConstraint("telefone", name="prestador_telefone_unico"),
        CheckConstraint(
            f"char_length(nome) between {MIN_NOME} and {LIMITE_NOME} and nome = btrim(nome)",
            name="prestador_nome_tamanho",
        ),
        CheckConstraint(
            "telefone ~ '^[1-9]{2}[0-9]{8,9}$'"
            " and (char_length(telefone) = 10 or substr(telefone, 3, 1) = '9')",
            name="prestador_telefone_formato",
        ),
        CheckConstraint(
            f"instagram ~ '^[A-Za-z0-9._]{{1,{LIMITE_INSTAGRAM}}}$'",
            name="prestador_instagram_formato",
        ),
        CheckConstraint("char_length(nome_busca) > 0", name="prestador_nome_busca"),
        Index("prestador_categoria", "categoria_id"),
    )

    id: Mapped[int] = chave_primaria()
    categoria_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categoria_servico.id"))
    nome: Mapped[str]
    # O nome sem acento, minúsculo e com os espaços juntos (gravado pela API: `normalizar`).
    nome_busca: Mapped[str]
    # Só os dígitos, com DDD e sem o 55.
    telefone: Mapped[str]
    # Sem o @.
    instagram: Mapped[str | None]
    # Vira nulo em "apagar meus dados" e no reset: o próximo morador não herda o direito de
    # corrigir.
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    editado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondido_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))


class OpiniaoServico(Base):
    """Recomendo ou não recomendo, uma por unidade e prestador. Escondida, fica travada."""

    __tablename__ = "opiniao_servico"
    __table_args__ = (
        UniqueConstraint("prestador_id", "unidade_id", name="opiniao_servico_unica"),
        CheckConstraint(
            _texto_opcional("comentario", LIMITE_COMENTARIO),
            name="opiniao_servico_comentario_tamanho",
        ),
        Index("opiniao_servico_unidade", "unidade_id", "criada_em"),
    )

    id: Mapped[int] = chave_primaria()
    prestador_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("prestador.id"))
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    recomenda: Mapped[bool]
    comentario: Mapped[str | None]
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())
    editada_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondida_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    escondida_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))


class AvisoServico(Base):
    """ "Tem algo errado aqui?": um aberto por unidade e prestador. Só a gestão vê."""

    __tablename__ = "aviso_servico"
    __table_args__ = (
        CheckConstraint(
            _texto_opcional("motivo", LIMITE_MOTIVO), name="aviso_servico_motivo_tamanho"
        ),
        Index(
            "aviso_servico_aberto",
            "prestador_id",
            "unidade_id",
            unique=True,
            postgresql_where=text("resolvido_em is null"),
        ),
    )

    id: Mapped[int] = chave_primaria()
    prestador_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("prestador.id"))
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    motivo: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    resolvido_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    resolvido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    # E-mails do primeiro aviso reservados na cota do Gmail (somados em
    # `notificacoes.emails_nas_ultimas_24h`).
    emails_reservados: Mapped[int] = mapped_column(SmallInteger, server_default="0")
