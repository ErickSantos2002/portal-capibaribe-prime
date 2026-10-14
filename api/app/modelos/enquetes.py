"""Enquetes (M4, migração 0008): `enquete`, `enquete_opcao`, `enquete_bloco`, `voto`,
`voto_opcao`. Spec: `docs/superpowers/specs/m4-contrato.md`, seção 2.

Regras que o banco garante e que estes modelos não repetem: datas carimbadas pelo banco; prazo
no futuro e em até 366 dias; enquete completa no commit (2 a 10 opções, destino); destino só na
criação; **nada muda depois do 1º voto nem depois do encerramento**; **um voto por unidade**
(chave primária); **nada de voto depois do prazo**; voto só de quem está no destino; voto
completo no commit (escolha única = uma opção); o `app` não apaga enquete, destino nem voto.

Gravar o voto sempre nesta ordem, numa transação (spec, seção 2.6): `insert into voto … on
conflict do update set votado_em = excluded.votado_em`, depois apagar e inserir as linhas de
`voto_opcao` da unidade.
"""

from datetime import datetime, timedelta

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    FetchedValue,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria

LIMITE_PERGUNTA = 200
LIMITE_OPCAO = 100
MIN_OPCOES = 2
MAX_OPCOES = 10
# O banco aceita o término no futuro e até 366 dias à frente, pelo relógio dele. A API pede mais
# (de 1 hora a 365 dias, pelo relógio dela): o que a API aceita, o banco aceita, mesmo com os
# relógios um pouco diferentes e o tempo entre a conferência e a gravação (revisão do contrato,
# achado 6). A tela fala em "1 ano".
DURACAO_MAXIMA_BANCO = timedelta(days=366)
DURACAO_MAXIMA = timedelta(days=365)
DURACAO_MINIMA = timedelta(hours=1)
# RF-23, na ordem do formulário; `durante` é o padrão.
MOSTRAR_RESULTADO = ("durante", "so_no_fim")


class Enquete(Base):
    __tablename__ = "enquete"
    __table_args__ = (
        CheckConstraint(
            f"char_length(btrim(pergunta)) between 1 and {LIMITE_PERGUNTA}"
            f" and char_length(pergunta) <= {LIMITE_PERGUNTA}",
            name="enquete_pergunta_tamanho",
        ),
        CheckConstraint(
            "mostrar_resultado in (" + ", ".join(f"'{m}'" for m in MOSTRAR_RESULTADO) + ")",
            name="enquete_mostrar_resultado",
        ),
        CheckConstraint("encerra_em > criada_em", name="enquete_prazo"),
        Index("enquete_encerra_em", "encerra_em"),
    )

    id: Mapped[int] = chave_primaria()
    pergunta: Mapped[str]
    multipla_escolha: Mapped[bool] = mapped_column(server_default="false")
    mostrar_resultado: Mapped[str] = mapped_column(server_default="durante")
    encerra_em: Mapped[datetime]
    # `False` = só os blocos em `enquete_bloco`. Não muda depois de criada.
    para_todos: Mapped[bool]
    criada_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    criada_em: Mapped[datetime] = mapped_column(server_default=func.now())
    # Carimbada pelo banco a cada edição (antes do 1º voto).
    editada_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    # Gravada pelo primeiro voto (trigger); daí em diante nada muda na enquete.
    primeiro_voto_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
    # O aviso automático (H-13), criado na mesma transação.
    aviso_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("aviso.id"), unique=True)


class EnqueteOpcao(Base):
    """De 2 a 10 por enquete. Editar = apagar e inserir de novo (o `app` não tem UPDATE)."""

    __tablename__ = "enquete_opcao"
    __table_args__ = (
        CheckConstraint(
            f"char_length(btrim(texto)) between 1 and {LIMITE_OPCAO}"
            f" and char_length(texto) <= {LIMITE_OPCAO}",
            name="enquete_opcao_texto_tamanho",
        ),
        CheckConstraint(f"ordem between 1 and {MAX_OPCOES}", name="enquete_opcao_ordem"),
        UniqueConstraint("enquete_id", "ordem", name="enquete_opcao_ordem_unica"),
        UniqueConstraint("enquete_id", "texto", name="enquete_opcao_texto_unico"),
        UniqueConstraint("enquete_id", "id", name="enquete_opcao_da_enquete"),
    )

    id: Mapped[int] = chave_primaria()
    enquete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enquete.id"))
    texto: Mapped[str]
    ordem: Mapped[int] = mapped_column(SmallInteger)


class EnqueteBloco(Base):
    """Destino quando `enquete.para_todos` é falso. Só entra na criação."""

    __tablename__ = "enquete_bloco"
    __table_args__ = (Index("enquete_bloco_bloco", "bloco_id"),)

    enquete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enquete.id"), primary_key=True)
    bloco_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("bloco.id"), primary_key=True)


class Voto(Base):
    """A participação da unidade (H-21). A chave primária é o "um voto por unidade" (RN-01)."""

    __tablename__ = "voto"
    __table_args__ = (Index("voto_unidade", "unidade_id"),)

    enquete_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("enquete.id"), primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"), primary_key=True)
    # Carimbada pelo banco; atualizada quando o voto é trocado.
    votado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class VotoOpcao(Base):
    """Uma linha por opção marcada. Trocar o voto apaga e insere de novo."""

    __tablename__ = "voto_opcao"
    __table_args__ = (
        ForeignKeyConstraint(
            ["enquete_id", "unidade_id"],
            ["voto.enquete_id", "voto.unidade_id"],
            name="voto_opcao_do_voto",
        ),
        ForeignKeyConstraint(
            ["enquete_id", "opcao_id"],
            ["enquete_opcao.enquete_id", "enquete_opcao.id"],
            name="voto_opcao_da_enquete",
        ),
        Index("voto_opcao_opcao", "enquete_id", "opcao_id"),
    )

    enquete_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    opcao_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
