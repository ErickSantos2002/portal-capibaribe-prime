"""Indicações de serviços (spec de 18/10/2026, seções 3, 4 e 7).

Espelho TypeScript: `web/src/indicacoes/tipos.ts` (conferido por `testes/test_contrato.py`).
Nas respostas, `None` nos campos da gestão quer dizer "não é para você".
"""

import re
import unicodedata
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator

from app.esquemas.comum import (
    Entrada,
    IdBanco,
    Saida,
    UnidadeRef,
    sem_controle,
    sem_invisiveis,
    sem_invisivel_nenhum,
)
from app.modelos.indicacoes import (
    LIMITE_CATEGORIA,
    LIMITE_COMENTARIO,
    LIMITE_INSTAGRAM,
    LIMITE_MOTIVO,
    LIMITE_NOME,
    MIN_NOME,
)

# O mesmo formato do check `prestador_telefone_formato`: DDD sem zero e, depois dele, celular
# (9 e mais 8 dígitos) ou fixo (começa de 2 a 5, com 8 dígitos).
_TELEFONE = re.compile(r"[1-9]{2}(?:9[0-9]{8}|[2-5][0-9]{7})")
_INSTAGRAM = re.compile(rf"[A-Za-z0-9._]{{1,{LIMITE_INSTAGRAM}}}")
MSG_TELEFONE = "Escreva o WhatsApp ou o telefone com DDD, por exemplo (81) 9 9999-0001."


def validar_telefone(valor: object) -> str:
    """Aceita máscara, espaço e `+55`; guarda só os dígitos, sem o 55. Celular escrito sem o
    nono dígito ("(81) 9999-0001", 10 dígitos com o terceiro de 6 a 9) ganha o 9: senão o mesmo
    prestador entraria duas vezes, uma com e outra sem."""
    if not isinstance(valor, str):
        raise ValueError(MSG_TELEFONE)
    digitos = "".join(c for c in valor if c.isascii() and c.isdigit())
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) == 10 and digitos[2] in "6789":
        digitos = f"{digitos[:2]}9{digitos[2:]}"
    if not _TELEFONE.fullmatch(digitos):
        raise ValueError(MSG_TELEFONE)
    return digitos


def validar_instagram(valor: object) -> str | None:
    """`@usuario` ou `usuario`; guarda sem o @. Em branco vira nulo."""
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ValueError("Escreva o Instagram como @usuario.")
    valor = valor.strip()
    if not valor:
        return None
    valor = valor.removeprefix("@")
    if not _INSTAGRAM.fullmatch(valor):
        raise ValueError(
            f"Escreva o Instagram como @usuario, com até {LIMITE_INSTAGRAM} letras, números,"
            " ponto ou sublinhado."
        )
    return valor


def _linha(texto: str, minimo: int, maximo: int, vazio: str) -> str:
    sem_invisivel_nenhum(texto)
    # NFC antes de contar e de gravar: "é" e "e + acento" são a mesma letra.
    texto = unicodedata.normalize("NFC", texto).strip()
    if not texto:
        raise ValueError(vazio)
    if len(texto) < minimo:
        raise ValueError(f"Escreva pelo menos {minimo} letras.")
    if len(texto) > maximo:
        raise ValueError(f"Pode ter até {maximo} letras.")
    return texto


def validar_nome(nome: str) -> str:
    return _linha(nome, MIN_NOME, LIMITE_NOME, "Escreva o nome do prestador ou da empresa.")


def validar_nome_categoria(nome: str) -> str:
    return _linha(nome, MIN_NOME, LIMITE_CATEGORIA, "Escreva o nome da categoria.")


def _texto_livre(limite: int):
    def validar(texto: str | None) -> str | None:
        if texto is None:
            return None
        sem_controle(texto, permitidos="\n")
        sem_invisiveis(texto)
        texto = unicodedata.normalize("NFC", texto).strip()
        if not texto:
            return None
        if len(texto) > limite:
            raise ValueError(f"Pode ter até {limite} letras.")
        return texto

    return validar


Telefone = Annotated[str, BeforeValidator(validar_telefone)]
Instagram = Annotated[str | None, BeforeValidator(validar_instagram)]
NomePrestador = Annotated[str, AfterValidator(validar_nome)]
NomeCategoria = Annotated[str, AfterValidator(validar_nome_categoria)]
Comentario = Annotated[str | None, AfterValidator(_texto_livre(LIMITE_COMENTARIO))]
Motivo = Annotated[str | None, AfterValidator(_texto_livre(LIMITE_MOTIVO))]


# --- requisições -------------------------------------------------------------------------------


class NovaIndicacao(Entrada):
    """`POST /api/indicacoes`: o prestador e a primeira opinião, numa transação. `recomenda` não
    tem padrão (a tela não deixa marcado)."""

    categoria_id: IdBanco
    nome: NomePrestador
    telefone: Telefone
    instagram: Instagram = None
    recomenda: bool
    comentario: Comentario = None


class CorrigirPrestador(Entrada):
    """`PUT /api/indicacoes/{id}`: quem indicou ou a gestão. Tudo de novo (o Instagram nulo
    apaga)."""

    categoria_id: IdBanco
    nome: NomePrestador
    telefone: Telefone
    instagram: Instagram = None


class DarOpiniao(Entrada):
    """`PUT /api/indicacoes/{id}/opiniao`: dar e mudar são a mesma coisa."""

    recomenda: bool
    comentario: Comentario = None


class AvisarGestao(Entrada):
    """`POST /api/indicacoes/{id}/aviso`: "Tem algo errado aqui?"."""

    motivo: Motivo = None


class NovaCategoria(Entrada):
    """`POST /api/indicacoes/categorias` (administração): entra antes de "Outros"."""

    nome: NomeCategoria


class RenomearCategoria(Entrada):
    """`PUT /api/indicacoes/categorias/{id}` (administração)."""

    nome: NomeCategoria


# --- respostas ---------------------------------------------------------------------------------


class CategoriaServico(Saida):
    id: int
    nome: str


class ListaCategorias(Saida):
    """`GET /api/indicacoes/categorias`: na ordem, "Outros" por último."""

    itens: list[CategoriaServico]


class OpiniaoTrecho(Saida):
    """A opinião visível mais recente com comentário, no cartão da lista."""

    unidade: UnidadeRef
    comentario: str
    em: datetime


class PrestadorResumo(Saida):
    """Cartão da lista."""

    id: int
    categoria: CategoriaServico
    nome: str
    # Só as opiniões visíveis.
    recomendam: int
    nao_recomendam: int
    trecho: OpiniaoTrecho | None
    # Avisos abertos (só a gestão; nulo para o morador).
    avisos_abertos: int | None


class ListaIndicacoes(Saida):
    """`GET /api/indicacoes`: mais recomendados primeiro; no empate, a opinião mais recente."""

    itens: list[PrestadorResumo]
    # Quantos prestadores têm aviso aberto (só a gestão; nulo para o morador).
    com_aviso: int | None


class PrestadorRef(Saida):
    id: int
    nome: str
    categoria: CategoriaServico


class Parecidos(Saida):
    """`GET /api/indicacoes/parecidos?nome=`: até 3, para o aviso de duplicado."""

    itens: list[PrestadorRef]


class Opiniao(Saida):
    """Uma opinião visível, com a placa da unidade (nunca o nome de ninguém)."""

    id: int
    unidade: UnidadeRef
    recomenda: bool
    comentario: str | None
    # A mais recente entre criada e editada.
    em: datetime
    # É a opinião da unidade logada.
    minha: bool


class MinhaOpiniao(Saida):
    """O que a unidade logada escreveu. `escondida`: a gestão escondeu, e ela não muda mais."""

    recomenda: bool
    comentario: str | None
    escondida: bool


class AvisoRecebido(Saida):
    """Aviso aberto, para a gestão. Sem a placa de quem avisou."""

    id: int
    motivo: str | None
    em: datetime


class Prestador(Saida):
    """`GET /api/indicacoes/{id}` e a resposta de opinar e de corrigir."""

    id: int
    categoria: CategoriaServico
    nome: str
    # Só os dígitos, com DDD.
    telefone: str
    # 11 dígitos: o "Ligar" só aparece quando é falso.
    celular: bool
    instagram: str | None
    recomendam: int
    nao_recomendam: int
    # Visíveis, da mais recente para a mais antiga.
    opinioes: list[Opiniao]
    minha_opiniao: MinhaOpiniao | None
    # Quem indicou ou a gestão.
    pode_corrigir: bool
    # A unidade logada tem aviso aberto aqui.
    ja_avisei: bool
    # Só a gestão vê um escondido.
    escondido: bool
    # Avisos abertos (só a gestão; nulo para o morador).
    avisos: list[AvisoRecebido] | None


class IndicacaoCriada(Saida):
    """Resposta de indicar: a tela vai para `/indicacoes/{id}`."""

    id: int
