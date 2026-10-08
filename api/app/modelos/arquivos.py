"""Arquivo enviado ao bucket (M3, migração 0007): `arquivo`. Spec:
`docs/superpowers/specs/m3-contrato.md`, seção 2.1; guarda dos arquivos: ADR-0011.

Regras que o banco garante e que este modelo não repete: datas carimbadas pelo banco; pendente
pode ter `tipo` e `tamanho_bytes` corrigidos e ser apagado; confirmado não muda nem é apagado;
até 50 por unidade a cada 24 horas.
"""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, FetchedValue, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.modelos.base import Base, chave_primaria

# A ordem é a das mensagens ("PDF e fotos"). Conferidos pelo conteúdo, não pela extensão.
TIPOS_ACEITOS = ("application/pdf", "image/jpeg", "image/png", "image/webp")
FINALIDADES = ("aviso", "documento")
MB = 1024 * 1024
# Por envio: 10 MB no anexo de aviso (H-12), 20 MB no documento (H-17).
LIMITE_POR_FINALIDADE = {"aviso": 10 * MB, "documento": 20 * MB}
LIMITE_NOME = 200
ARQUIVOS_POR_DIA = 50


class Arquivo(Base):
    """O que foi enviado. O conteúdo mora no R2: `envios/<chave>` enquanto pendente,
    `arquivos/<chave>` depois de confirmado (nunca apagado, ADR-0011)."""

    __tablename__ = "arquivo"
    __table_args__ = (
        CheckConstraint("chave ~ '^[0-9a-f]{32}$'", name="arquivo_chave"),
        CheckConstraint(
            f"char_length(nome_original) between 1 and {LIMITE_NOME}"
            " and nome_original = btrim(nome_original)"
            " and nome_original !~ '[[:cntrl:]/\\\\]'",
            name="arquivo_nome",
        ),
        CheckConstraint(
            "tipo in (" + ", ".join(f"'{t}'" for t in TIPOS_ACEITOS) + ")", name="arquivo_tipo"
        ),
        CheckConstraint(
            "finalidade in (" + ", ".join(f"'{f}'" for f in FINALIDADES) + ")",
            name="arquivo_finalidade",
        ),
        CheckConstraint(
            f"tamanho_bytes between 1 and {LIMITE_POR_FINALIDADE['documento']}"
            f" and (finalidade = 'documento' or tamanho_bytes <= {LIMITE_POR_FINALIDADE['aviso']})",
            name="arquivo_tamanho",
        ),
        Index("arquivo_enviado", "enviado_por", "enviado_em"),
        Index("arquivo_pendente", "enviado_em", postgresql_where=text("confirmado_em is null")),
    )

    id: Mapped[int] = chave_primaria()
    chave: Mapped[str] = mapped_column(unique=True)
    nome_original: Mapped[str]
    tipo: Mapped[str]
    finalidade: Mapped[str]
    tamanho_bytes: Mapped[int]
    enviado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("unidade.id"))
    enviado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    # Nulo = pendente. Carimbado pelo banco (qualquer valor não nulo vira now()).
    confirmado_em: Mapped[datetime | None] = mapped_column(server_onupdate=FetchedValue())
