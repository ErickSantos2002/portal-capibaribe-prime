"""Épico A do M3 · Documentos (H-17, H-18, H-19; spec do M3, seção 5.2). Pertence ao épico A.

Espelho TypeScript: `web/src/documentos/tipos.ts`. O arquivo de cada versão já foi enviado e
conferido pela rota comum (`POST /api/arquivos`); aqui só vai o id dele.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, ValidationInfo, field_validator

from app.esquemas.arquivos import ArquivoEnviado
from app.esquemas.comum import (
    Entrada,
    IdBanco,
    Saida,
    sem_invisivel_nenhum,
)
from app.modelos.documentos import (
    DATA_DOCUMENTO_ATE,
    DATA_DOCUMENTO_DESDE,
    LIMITE_TITULO_DOCUMENTO,
)


class CategoriaDocumento(StrEnum):
    """Assunto do documento; a ordem é a das opções do formulário (protótipo)."""

    obra = "obra"
    convencao = "convencao"
    regimento = "regimento"
    ata = "ata"
    contrato = "contrato"
    orientacao = "orientacao"
    outro = "outro"


class NivelAcesso(StrEnum):
    """Quem vê (RF-31): qualquer visitante, as unidades que já entraram, ou só a gestão."""

    publico = "publico"
    compradores = "compradores"
    gestao = "gestao"


# A regra endurecida do título (revisão do épico A, C3) mora em `comum.py` desde o fechamento do
# M3 (vale também para o título do aviso); continua importável daqui.
_REEXPORTADOS = (sem_invisivel_nenhum,)


def validar_titulo(titulo: str) -> str:
    sem_invisivel_nenhum(titulo)
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("Escreva o título do documento.")
    if len(titulo) > LIMITE_TITULO_DOCUMENTO:
        raise ValueError("O título pode ter até 120 letras.")
    return titulo


def validar_data(data: date) -> date:
    if not DATA_DOCUMENTO_DESDE <= data <= DATA_DOCUMENTO_ATE:
        raise ValueError("Escolha uma data entre 1990 e 2100.")
    return data


def validar_nota(nota: str | None) -> str | None:
    """A linha opcional que a gestão escreve para o aviso automático (revisão UX, U3 e U13):
    uma linha só (espaços e quebras viram um espaço), até 300 letras; vazia é nenhuma."""
    if nota is None:
        return None
    sem_invisivel_nenhum(nota.replace("\n", " ").replace("\r", " ").replace("\t", " "))
    nota = " ".join(nota.split())
    if len(nota) > LIMITE_NOTA_DO_AVISO:
        raise ValueError(f"A linha do aviso pode ter até {LIMITE_NOTA_DO_AVISO} letras.")
    return nota or None


LIMITE_NOTA_DO_AVISO = 300
# Ids do banco são bigint (C2): fora disso, 422 em vez de erro 500 do banco. O tipo é o comum.
IdDoBanco = IdBanco
TituloDocumento = Annotated[str, AfterValidator(validar_titulo)]
DataDocumento = Annotated[date, AfterValidator(validar_data)]
NotaDoAviso = Annotated[str | None, AfterValidator(validar_nota)]
MSG_SO_VISIVEL = "Só dá para avisar as unidades de documento que elas podem ver."


# --- requisições -------------------------------------------------------------------------------


class NovoDocumento(Entrada):
    """`POST /api/documentos` (H-17). `arquivo_id`: arquivo confirmado, de finalidade
    `documento`, enviado pela própria unidade. `avisar_unidades` (RF-33) cria o aviso
    automático, só para documento que as unidades podem ver."""

    titulo: TituloDocumento
    categoria: CategoriaDocumento
    data_documento: DataDocumento
    acesso: NivelAcesso
    arquivo_id: IdDoBanco
    avisar_unidades: bool = False
    # A linha que a gestão escreve para o aviso automático (revisão UX, U13). Sem aviso, ignorada.
    nota_do_aviso: NotaDoAviso = None

    @field_validator("avisar_unidades")
    @classmethod
    def _avisar(cls, avisar: bool, info: ValidationInfo) -> bool:
        if avisar and info.data.get("acesso") == NivelAcesso.gestao:
            raise ValueError(MSG_SO_VISIVEL)
        return avisar


class NovaVersaoDocumento(Entrada):
    """`POST /api/documentos/{id}/versoes` (H-19): o arquivo da versão nova e, se quiser, o
    aviso para as unidades com "o que mudou" (revisão UX, U3; desmarcado por padrão)."""

    arquivo_id: IdDoBanco
    avisar_unidades: bool = False
    nota_do_aviso: NotaDoAviso = None


# --- respostas ---------------------------------------------------------------------------------


class VersaoDocumento(Saida):
    versao: int
    enviada_em: datetime
    arquivo: ArquivoEnviado


class DocumentoResumo(Saida):
    """Item da lista (H-18). `versao`, `atualizado_em` e `arquivo` são da versão atual."""

    id: int
    titulo: str
    categoria: CategoriaDocumento
    data_documento: date
    acesso: NivelAcesso
    versao: int
    atualizado_em: datetime
    arquivo: ArquivoEnviado
    arquivado_em: datetime | None


class Documento(DocumentoResumo):
    """`GET /api/documentos/{id}` e respostas de publicar, nova versão e arquivar."""

    # Da mais nova para a mais antiga, sem a atual ("Versões anteriores", H-19).
    versoes_anteriores: list[VersaoDocumento]
    # O aviso automático de "Avisar as unidades" (RF-33), se houve.
    aviso_id: int | None


class ListaDocumentos(Saida):
    """`GET /api/documentos` e `GET /api/documentos/publicos`: data do documento, da mais nova
    para a mais antiga (a tela agrupa por categoria e busca pelo título)."""

    itens: list[DocumentoResumo]
