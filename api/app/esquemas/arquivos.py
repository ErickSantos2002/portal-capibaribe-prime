"""Comum · Envio de arquivo (spec do M3, seção 5.1). Arquivo comum: os épicos usam, não editam.

Espelho TypeScript: `web/src/arquivos/tipos.ts`. O conteúdo do arquivo nunca vem na
requisição: a API dá a URL assinada e confere depois (`app/servicos/arquivos.py`).
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, Field, ValidationInfo, field_validator

from app.esquemas.comum import Entrada, Saida, sem_controle, sem_invisiveis
from app.modelos.arquivos import LIMITE_NOME, LIMITE_POR_FINALIDADE, MB

MSG_TIPO = "O Portal aceita PDF e fotos (JPEG, PNG ou WEBP)."


class TipoArquivo(StrEnum):
    pdf = "application/pdf"
    jpeg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"


class Finalidade(StrEnum):
    """Para onde vai o arquivo: decide o limite (10 MB no aviso, 20 MB no documento)."""

    aviso = "aviso"
    documento = "documento"


def mensagem_do_limite(finalidade: Finalidade | str) -> str:
    return f"O arquivo pode ter até {LIMITE_POR_FINALIDADE[str(finalidade)] // MB} MB."


def validar_nome(nome: str) -> str:
    """O nome do arquivo no aparelho: só um rótulo (o objeto no bucket nunca usa este nome)."""
    sem_controle(nome)
    sem_invisiveis(nome)
    nome = nome.strip()
    if not nome:
        raise ValueError("O arquivo precisa ter um nome.")
    if "/" in nome or "\\" in nome:
        raise ValueError("O nome do arquivo não pode ter barra.")
    if len(nome) > LIMITE_NOME:
        raise ValueError("O nome do arquivo pode ter até 200 letras.")
    return nome


NomeDeArquivo = Annotated[str, AfterValidator(validar_nome)]


# --- requisições -------------------------------------------------------------------------------


class PedirEnvio(Entrada):
    """`POST /api/arquivos`: a URL para o navegador mandar o arquivo direto ao bucket."""

    nome: NomeDeArquivo
    tipo: TipoArquivo
    finalidade: Finalidade
    # O tamanho do arquivo como vai ser enviado (depois de comprimir, se for foto).
    tamanho_bytes: int = Field(ge=1)

    @field_validator("tipo", mode="before")
    @classmethod
    def _tipo(cls, tipo: Any) -> Any:
        if tipo not in {t.value for t in TipoArquivo}:
            raise ValueError(MSG_TIPO)
        return tipo

    @field_validator("tamanho_bytes")
    @classmethod
    def _tamanho(cls, tamanho: int, info: ValidationInfo) -> int:
        finalidade = info.data.get("finalidade")
        if finalidade is not None and tamanho > LIMITE_POR_FINALIDADE[str(finalidade)]:
            raise ValueError(mensagem_do_limite(finalidade))
        return tamanho


# --- respostas ---------------------------------------------------------------------------------


class EnvioAutorizado(Saida):
    """Para onde o navegador manda o arquivo: `PUT url`, com o cabeçalho `Content-Type` igual a
    `content_type` (ele entra na assinatura) e sem cookie. Vale até `expira_em` (10 minutos)."""

    arquivo_id: int
    url: str
    content_type: str
    expira_em: datetime


class ArquivoEnviado(Saida):
    """Um arquivo conferido e publicado: como ele aparece no documento e no aviso. `tipo` e
    `tamanho_bytes` são os que o servidor achou no arquivo, não os declarados."""

    id: int
    nome: str
    tipo: TipoArquivo
    tamanho_bytes: int


class LinkDoArquivo(Saida):
    """Link assinado (1 hora) para abrir ou baixar. Pedido na hora do toque, nunca guardado."""

    url: str
    expira_em: datetime
