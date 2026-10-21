"""Classificados entre vizinhos (spec de 20/10/2026, seções 3, 4 e 8).

Espelho TypeScript: `web/src/classificados/tipos.ts` (conferido por `testes/test_contrato.py`).
Nas respostas, `None` nos campos da gestão quer dizer "não é para você". O aviso à gestão, o aviso
recebido e as categorias da administração usam os mesmos esquemas das indicações
(`AvisarGestao`, `AvisoRecebido`, `NovaCategoria`, `RenomearCategoria`).
"""

import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, Field, ValidationInfo, field_validator

from app.esquemas.comum import (
    Entrada,
    IdBanco,
    Saida,
    UnidadeRef,
    sem_controle,
    sem_invisiveis,
    sem_invisivel_nenhum,
)
from app.esquemas.indicacoes import AvisoRecebido, Telefone
from app.modelos.classificados import (
    FOTOS_POR_ANUNCIO,
    LIMITE_DESCRICAO,
    LIMITE_FOTO,
    LIMITE_TITULO,
    MB,
    MIN_TITULO,
    PRECO_MAXIMO,
    MotivoEncerramento,
    SituacaoAnuncio,
    TipoAnuncio,
)

__all__ = ["MotivoEncerramento", "SituacaoAnuncio", "TipoAnuncio", "TipoFoto"]

MSG_TIPO_FOTO = "O Portal aceita fotos em JPEG, PNG ou WEBP."
MSG_TAMANHO_FOTO = f"A foto pode ter até {LIMITE_FOTO // MB} MB."
MSG_PRECO = "O preço vai de R$ 0 a R$ 100.000."
MSG_PRECO_SO_NA_VENDA = "Só a venda tem preço."


class TipoFoto(StrEnum):
    jpeg = "image/jpeg"
    png = "image/png"
    webp = "image/webp"


def validar_titulo(titulo: str) -> str:
    sem_invisivel_nenhum(titulo)
    titulo = unicodedata.normalize("NFC", titulo).strip()
    if not titulo:
        raise ValueError("Escreva o que você está anunciando.")
    if len(titulo) < MIN_TITULO:
        raise ValueError(f"Escreva pelo menos {MIN_TITULO} letras.")
    if len(titulo) > LIMITE_TITULO:
        raise ValueError(f"Pode ter até {LIMITE_TITULO} letras.")
    return titulo


def validar_descricao(texto: str | None) -> str | None:
    if texto is None:
        return None
    sem_controle(texto, permitidos="\n")
    sem_invisiveis(texto)
    texto = unicodedata.normalize("NFC", texto).strip()
    if not texto:
        return None
    if len(texto) > LIMITE_DESCRICAO:
        raise ValueError(f"Pode ter até {LIMITE_DESCRICAO} letras.")
    return texto


def validar_fotos(fotos: list[int]) -> list[int]:
    if len(fotos) > FOTOS_POR_ANUNCIO:
        raise ValueError(f"No máximo {FOTOS_POR_ANUNCIO} fotos.")
    if len(set(fotos)) != len(fotos):
        raise ValueError("A mesma foto apareceu duas vezes. Envie as fotos de novo.")
    return fotos


Titulo = Annotated[str, AfterValidator(validar_titulo)]
Descricao = Annotated[str | None, AfterValidator(validar_descricao)]
Fotos = Annotated[list[IdBanco], AfterValidator(validar_fotos)]


# --- requisições -------------------------------------------------------------------------------


class NovoAnuncio(Entrada):
    """`POST /api/classificados` e `PUT /api/classificados/{id}`. `tipo` não tem padrão (a tela não
    deixa marcado). `fotos`: as ids na ordem, a primeira é a capa (as já enviadas e confirmadas;
    no editar, também as que já estão no anúncio)."""

    tipo: TipoAnuncio
    categoria_id: IdBanco
    titulo: Titulo
    descricao: Descricao = None
    # Só na venda; nulo = "a combinar".
    preco_centavos: int | None = None
    contato: Telefone
    fotos: Fotos = Field(default_factory=list)

    @field_validator("preco_centavos")
    @classmethod
    def _preco(cls, preco: int | None, info: ValidationInfo) -> int | None:
        if preco is None:
            return None
        if info.data.get("tipo") not in (None, TipoAnuncio.venda):
            raise ValueError(MSG_PRECO_SO_NA_VENDA)
        if not 0 <= preco <= PRECO_MAXIMO:
            raise ValueError(MSG_PRECO)
        return preco


class EncerrarAnuncio(Entrada):
    """`POST /api/classificados/{id}/encerrar` (o dono): Vendi · Troquei · Doei · Desisti."""

    motivo: MotivoEncerramento


class PedirFoto(Entrada):
    """`POST /api/classificados/fotos`: a URL para o navegador mandar a foto direto ao bucket."""

    tipo: TipoFoto
    # O tamanho da foto como vai ser enviada (depois de comprimir).
    tamanho_bytes: int

    @field_validator("tipo", mode="before")
    @classmethod
    def _tipo(cls, tipo: Any) -> Any:
        if tipo not in {t.value for t in TipoFoto}:
            raise ValueError(MSG_TIPO_FOTO)
        return tipo

    @field_validator("tamanho_bytes")
    @classmethod
    def _tamanho(cls, tamanho: int) -> int:
        if tamanho < 1:
            raise ValueError("A foto está vazia. Escolha outra.")
        if tamanho > LIMITE_FOTO:
            raise ValueError(MSG_TAMANHO_FOTO)
        return tamanho


# --- respostas ---------------------------------------------------------------------------------


class CategoriaClassificado(Saida):
    id: int
    nome: str


class ListaCategoriasClassificado(Saida):
    """`GET /api/classificados/categorias`: na ordem, "Outros" por último."""

    itens: list[CategoriaClassificado]


class FotoAutorizada(Saida):
    """Para onde o navegador manda a foto: `PUT url`, com `Content-Type` igual a `content_type`
    e sem cookie. Vale até `expira_em` (10 minutos)."""

    foto_id: int
    url: str
    content_type: str
    expira_em: datetime


class FotoEnviada(Saida):
    """A foto conferida e guardada em `classificados/`: a id entra no anúncio."""

    id: int


class FotoDoAnuncio(Saida):
    """`url`: link assinado de 1 hora (pedir de novo abrindo o anúncio, nunca guardar)."""

    id: int
    url: str


class AnuncioResumo(Saida):
    """Cartão da lista e de "Meus anúncios"."""

    id: int
    tipo: TipoAnuncio
    categoria: CategoriaClassificado
    titulo: str
    preco_centavos: int | None
    # Link assinado da primeira foto, ou nulo (sem foto, ou arquivos desligados).
    capa: str | None
    unidade: UnidadeRef
    # A publicação ou a última renovação.
    em: datetime
    situacao: SituacaoAnuncio
    vencido: bool
    escondido: bool
    # Até quando fica na lista ("Fica na lista até 19 de novembro", em "Meus anúncios").
    vence_em: datetime
    # Avisos abertos (só a gestão, e nunca nos da própria unidade; nulo para os outros).
    avisos_abertos: int | None


class ListaClassificados(Saida):
    """`GET /api/classificados`: ativos e reservados, não vencidos nem escondidos, o mais recente
    primeiro."""

    itens: list[AnuncioResumo]
    # Quantos anúncios têm aviso aberto (só a gestão; nulo para o morador).
    com_aviso: int | None
    # Quantos anúncios a unidade logada tem (todos os estados): a entrada "Meus anúncios".
    meus: int
    # Desses, os abertos (não encerrados nem vencidos): o número ao lado de "Meus anúncios".
    meus_abertos: int


class MeusAnuncios(Saida):
    """`GET /api/classificados/meus`: todos os da unidade, enquanto existirem."""

    itens: list[AnuncioResumo]
    # A frase do limite que a unidade já bateu (5 por dia, 10 abertos), ou nulo: a tela de
    # anunciar avisa logo ao abrir.
    limite: str | None


class Anuncio(Saida):
    """`GET /api/classificados/{id}` e a resposta do que o dono faz."""

    id: int
    tipo: TipoAnuncio
    categoria: CategoriaClassificado
    titulo: str
    descricao: str | None
    preco_centavos: int | None
    # Só os dígitos, com DDD.
    contato: str
    # 11 dígitos: sem o WhatsApp, a tela mostra "Ligar".
    celular: bool
    unidade: UnidadeRef
    publicado_em: datetime
    renovado_em: datetime | None
    vence_em: datetime
    situacao: SituacaoAnuncio
    motivo_encerramento: MotivoEncerramento | None
    vencido: bool
    escondido: bool
    # Na ordem; a primeira é a capa.
    fotos: list[FotoDoAnuncio]
    # A unidade logada é a dona.
    meu: bool
    # O dono pode renovar agora (vencido ou a menos de 7 dias de vencer, aberto, não escondido).
    pode_renovar: bool
    ja_avisei: bool
    # Avisos abertos (só a gestão; nulo para o morador).
    avisos: list[AvisoRecebido] | None


class AnuncioCriado(Saida):
    """Resposta de anunciar: a tela vai para `/classificados/{id}`."""

    id: int


class ResultadoDaFaxina(Saida):
    """`GET /api/classificados/faxina` (Vercel Cron): quanto foi apagado nesta rodada."""

    anuncios: int
    fotos: int
