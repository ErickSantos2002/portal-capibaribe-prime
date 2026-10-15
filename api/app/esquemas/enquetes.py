"""Enquetes (M4; spec do M4, seção 3.2). Comum aos dois épicos: A cria e edita, B vota e mostra
o resultado.

Espelho TypeScript: `web/src/enquetes/tipos.ts` (conferido por `testes/test_contrato.py`).
"""

import unicodedata
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, Field, Strict, ValidationInfo, field_validator

from app.esquemas.avisos import NumeroDeBloco
from app.esquemas.comum import Entrada, IdBanco, Saida, UnidadeRef, sem_invisivel_nenhum
from app.modelos.enquetes import (
    DURACAO_MAXIMA,
    DURACAO_MINIMA,
    LIMITE_OPCAO,
    LIMITE_PERGUNTA,
    MAX_OPCOES,
    MIN_OPCOES,
)


class MostrarResultado(StrEnum):
    """Quando o resultado aparece (RF-23). Na ordem do formulário; `durante` é o padrão."""

    durante = "durante"
    so_no_fim = "so_no_fim"


def _tem_letra_ou_numero(texto: str) -> bool:
    """Revisão do épico A, ponto 6: um texto só de acentos soltos ou pontuação não aparece."""
    return any(unicodedata.category(c)[0] in "LN" for c in texto)


def validar_pergunta(pergunta: str) -> str:
    sem_invisivel_nenhum(pergunta)
    # NFC antes de contar e de gravar: "é" e "e + acento" são a mesma letra (revisão, ponto 6).
    pergunta = unicodedata.normalize("NFC", pergunta).strip()
    if not pergunta:
        raise ValueError("Escreva a pergunta.")
    if not _tem_letra_ou_numero(pergunta):
        raise ValueError("Escreva a pergunta com letras ou números.")
    if len(pergunta) > LIMITE_PERGUNTA:
        raise ValueError(f"A pergunta pode ter até {LIMITE_PERGUNTA} letras.")
    return pergunta


def _comparavel(texto: str) -> str:
    """ "Sábado de manhã" e "sábado  de MANHÃ" são a mesma opção."""
    return " ".join(texto.casefold().split())


def validar_opcoes(opcoes: list[str]) -> list[str]:
    """Sem espaço nas pontas; as em branco são descartadas (o formulário pode mandar a caixa
    vazia que a pessoa abriu e não usou); de 2 a 10, sem repetir."""
    limpas = []
    for opcao in opcoes:
        sem_invisivel_nenhum(opcao)
        opcao = unicodedata.normalize("NFC", opcao).strip()
        if not opcao:
            continue
        if not _tem_letra_ou_numero(opcao):
            raise ValueError("Cada opção precisa ter letras ou números.")
        if len(opcao) > LIMITE_OPCAO:
            raise ValueError(f"Cada opção pode ter até {LIMITE_OPCAO} letras.")
        limpas.append(opcao)
    if len(limpas) < MIN_OPCOES:
        raise ValueError("Escreva pelo menos 2 opções de resposta.")
    if len(limpas) > MAX_OPCOES:
        raise ValueError(f"O limite é de {MAX_OPCOES} opções.")
    if len({_comparavel(o) for o in limpas}) < len(limpas):
        raise ValueError("Duas opções estão iguais.")
    return limpas


MSG_TERMINO_MINIMO = "Escolha um término daqui a pelo menos 1 hora."


def validar_encerramento_editado(quando: datetime) -> datetime:
    """Com fuso, no futuro e em até 1 ano. O mínimo de 1 hora fica para quem chama: na edição,
    só vale se o término mudou (revisão do épico A, ponto 4)."""
    if quando.tzinfo is None or quando.utcoffset() is None:
        raise ValueError("Informe a hora com o fuso (ex.: -03:00).")
    agora = datetime.now(UTC)
    # O ano vem antes da conta: somar ao ano 9999 estoura o datetime (achado 1 do M1).
    if quando.year > agora.year + 2 or quando > agora + DURACAO_MAXIMA:
        raise ValueError("A enquete pode durar até 1 ano.")
    if quando <= agora:
        raise ValueError("A data de término já passou. Escolha uma data no futuro.")
    return quando


def termino_longe_o_bastante(quando: datetime) -> bool:
    return quando >= datetime.now(UTC) + DURACAO_MINIMA


def validar_encerramento(quando: datetime) -> datetime:
    validar_encerramento_editado(quando)
    if not termino_longe_o_bastante(quando):
        raise ValueError(MSG_TERMINO_MINIMO)
    return quando


Pergunta = Annotated[str, AfterValidator(validar_pergunta)]
Opcoes = Annotated[list[str], AfterValidator(validar_opcoes)]
Encerramento = Annotated[datetime, AfterValidator(validar_encerramento)]
EncerramentoEditado = Annotated[datetime, AfterValidator(validar_encerramento_editado)]


def validar_base(quando: datetime | None) -> datetime | None:
    if quando is not None and (quando.tzinfo is None or quando.utcoffset() is None):
        raise ValueError("Informe a hora com o fuso (ex.: -03:00).")
    return quando


# --- requisições -------------------------------------------------------------------------------


class EditarEnquete(Entrada):
    """`PUT /api/enquetes/{id}` (épico A): só enquanto ninguém votou e a enquete está aberta. O
    formulário manda tudo, sem padrão nenhum (revisão do épico A, ponto 9: campo esquecido não
    volta ao padrão em silêncio); as opções substituem as anteriores, na ordem. Destino não muda.

    `editada_em_base`: o `editada_em` da `Enquete` que a tela carregou (nulo se nunca foi
    editada). Se outra pessoa editou depois, 409 `enquete_mudou` (revisão, ponto 2). O término só
    pede "pelo menos 1 hora" se mudou (revisão, ponto 4; o serviço confere)."""

    pergunta: Pergunta
    opcoes: Opcoes
    multipla_escolha: bool
    encerra_em: EncerramentoEditado
    mostrar_resultado: MostrarResultado
    editada_em_base: Annotated[datetime | None, AfterValidator(validar_base)]


class NovaEnquete(Entrada):
    """`POST /api/enquetes` (H-20, épico A). `blocos` só vale quando `para_todos` é falso. Os
    padrões de `multipla_escolha` e `mostrar_resultado` ficam: na criação não há valor anterior
    para apagar sem querer."""

    pergunta: Pergunta
    opcoes: Opcoes
    multipla_escolha: bool = False
    encerra_em: Encerramento
    mostrar_resultado: MostrarResultado = MostrarResultado.durante
    para_todos: bool
    # `validate_default`: omitir `blocos` com `para_todos = false` também é recusado.
    blocos: list[NumeroDeBloco] = Field(default=[], validate_default=True)

    @field_validator("blocos")
    @classmethod
    def _blocos(cls, blocos: list[int], info: ValidationInfo) -> list[int]:
        if info.data.get("para_todos", True):
            return []
        if not blocos:
            raise ValueError("Escolha pelo menos um bloco, ou Todos os blocos.")
        return sorted(set(blocos))


class Votar(Entrada):
    """`PUT /api/enquetes/{id}/voto` (H-21, épico B): votar e trocar o voto são a mesma coisa.
    Mais de uma opção numa enquete de escolha única: a API recusa com 422 (e o banco também)."""

    # Inteiro estrito (revisão do épico B, ponto 7): `true`, `"1"` e `1.0` não viram a opção 1.
    opcoes: list[Annotated[IdBanco, Strict()]]

    @field_validator("opcoes")
    @classmethod
    def _opcoes(cls, opcoes: list[int]) -> list[int]:
        if not opcoes:
            raise ValueError("Escolha uma opção.")
        if len(opcoes) > MAX_OPCOES:
            raise ValueError(f"Escolha no máximo {MAX_OPCOES} opções.")
        if len(set(opcoes)) < len(opcoes):
            raise ValueError("A mesma opção foi escolhida duas vezes.")
        return opcoes


# --- respostas ---------------------------------------------------------------------------------


class OpcaoEnquete(Saida):
    id: int
    texto: str
    # Nulo enquanto o resultado está escondido ("só no fim" e ainda aberta).
    votos: int | None


class Participacao(Saida):
    """Quantas unidades votaram, de quantas unidades ativas do destino (H-22)."""

    votaram: int
    total: int


class EnqueteResumo(Saida):
    """Item da lista (épico B)."""

    id: int
    pergunta: str
    multipla_escolha: bool
    mostrar_resultado: MostrarResultado
    encerra_em: datetime
    # Pelo relógio da API, na hora da resposta.
    encerrada: bool
    para_todos: bool
    blocos: list[int]
    criada_em: datetime
    editada_em: datetime | None
    # A unidade logada já votou ("Seu apartamento ainda não votou" quando falso e aberta).
    ja_votou: bool


class Enquete(EnqueteResumo):
    """`GET /api/enquetes/{id}` e a resposta do voto (épico B)."""

    opcoes: list[OpcaoEnquete]
    # Ids das opções que a unidade marcou; `[]` se não votou.
    meu_voto: list[int]
    votado_em: datetime | None
    participacao: Participacao
    # Falso enquanto é "só no fim" e ainda está aberta (para todos, inclusive a gestão).
    resultado_visivel: bool
    # Aberta e a unidade no destino.
    pode_votar: bool
    # Gestão, aberta e sem voto nenhum.
    pode_editar: bool
    aviso_id: int


class ListaEnquetes(Saida):
    """`GET /api/enquetes`: abertas primeiro (a que termina antes no topo), depois as
    encerradas (a que terminou por último no topo)."""

    itens: list[EnqueteResumo]


class EnqueteGravada(Saida):
    """Resposta de criar e editar (épico A): a tela vai para `/enquetes/{id}`."""

    id: int
    aviso_id: int


class Votantes(Saida):
    """`GET /api/enquetes/{id}/votantes` (H-22, só a gestão): quais unidades votaram, nunca em
    quê. Por login."""

    votaram: list[UnidadeRef]
    entraram_sem_votar: list[UnidadeRef]
    nao_entraram: list[UnidadeRef]
