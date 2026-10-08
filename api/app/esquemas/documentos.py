"""Épico A do M3 · Documentos (H-17, H-18, H-19; spec do M3, seção 5.2). Pertence ao épico A.

Espelho TypeScript: `web/src/documentos/tipos.ts`. O arquivo de cada versão já foi enviado e
conferido pela rota comum (`POST /api/arquivos`); aqui só vai o id dele.
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, ValidationInfo, field_validator

from app.esquemas.arquivos import ArquivoEnviado
from app.esquemas.comum import Entrada, Saida, sem_controle, sem_invisiveis
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


def validar_titulo(titulo: str) -> str:
    sem_controle(titulo)
    sem_invisiveis(titulo)
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


TituloDocumento = Annotated[str, AfterValidator(validar_titulo)]
DataDocumento = Annotated[date, AfterValidator(validar_data)]


# --- requisições -------------------------------------------------------------------------------


class NovoDocumento(Entrada):
    """`POST /api/documentos` (H-17). `arquivo_id`: arquivo confirmado, de finalidade
    `documento`, enviado pela própria unidade. `avisar_unidades` (RF-33) cria o aviso
    automático, só para documento que as unidades podem ver."""

    titulo: TituloDocumento
    categoria: CategoriaDocumento
    data_documento: DataDocumento
    acesso: NivelAcesso
    arquivo_id: int
    avisar_unidades: bool = False

    @field_validator("avisar_unidades")
    @classmethod
    def _avisar(cls, avisar: bool, info: ValidationInfo) -> bool:
        if avisar and info.data.get("acesso") == NivelAcesso.gestao:
            raise ValueError("Só dá para avisar as unidades de documento que elas podem ver.")
        return avisar


class NovaVersaoDocumento(Entrada):
    """`POST /api/documentos/{id}/versoes` (H-19): o arquivo da versão nova."""

    arquivo_id: int


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
