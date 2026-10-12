"""Documentos (M3, migração 0007): `documento` e `documento_versao`. Spec:
`docs/superpowers/specs/m3-contrato.md`, seções 2.2 e 2.3.

Regras que o banco garante e que estes modelos não repetem: datas carimbadas pelo banco;
documento completo no commit (versão 1); versões em sequência, cada uma com um arquivo
confirmado de finalidade `documento` que não está em uso; arquivado não volta nem ganha versão;
o `app` não apaga nada daqui e só altera `documento.arquivado_em`.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, FetchedValue, ForeignKey, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria

# A ordem é a das opções do formulário (protótipo, `#novo-documento`); `outro` por último.
CATEGORIAS_DOCUMENTO = (
    "obra",
    "convencao",
    "regimento",
    "ata",
    "contrato",
    "orientacao",
    "outro",
)
# RF-31, do mais aberto ao mais fechado.
NIVEIS_ACESSO = ("publico", "compradores", "gestao")
LIMITE_TITULO_DOCUMENTO = 120
DATA_DOCUMENTO_DESDE = date(1990, 1, 1)
DATA_DOCUMENTO_ATE = date(2100, 12, 31)


class Documento(Base):
    __tablename__ = "documento"
    __table_args__ = (
        CheckConstraint(
            f"char_length(btrim(titulo)) between 1 and {LIMITE_TITULO_DOCUMENTO}"
            f" and char_length(titulo) <= {LIMITE_TITULO_DOCUMENTO}",
            name="documento_titulo_tamanho",
        ),
        CheckConstraint(
            "categoria in ('convencao', 'regimento', 'ata', 'contrato', 'obra', 'orientacao',"
            " 'outro')",
            name="documento_categoria",
        ),
        CheckConstraint(
            "data_documento between '1990-01-01' and '2100-12-31'", name="documento_data"
        ),
        CheckConstraint(
            "acesso in (" + ", ".join(f"'{n}'" for n in NIVEIS_ACESSO) + ")",
            name="documento_acesso",
        ),
        CheckConstraint("aviso_id is null or acesso <> 'gestao'", name="documento_aviso_gestao"),
    )

    id: Mapped[int] = chave_primaria()
    titulo: Mapped[str]
    categoria: Mapped[str]
    data_documento: Mapped[date]
    acesso: Mapped[str]
    criado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    # O aviso automático de "Avisar as unidades" (RF-33), gravado na criação.
    aviso_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("aviso.id"), unique=True)
    # Carimbado pelo banco ao arquivar (qualquer valor não nulo vira now()).
    arquivado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())


class DocumentoVersao(Base):
    """O arquivo de cada versão (H-19). A maior é a atual."""

    __tablename__ = "documento_versao"
    __table_args__ = (CheckConstraint("versao >= 1", name="documento_versao_minima"),)

    documento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documento.id"), primary_key=True
    )
    versao: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    arquivo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("arquivo.id"), unique=True)
    enviada_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    enviada_em: Mapped[datetime] = mapped_column(server_default=func.now())
