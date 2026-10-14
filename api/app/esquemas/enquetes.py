"""Enquetes (M4; spec do M4, seção 3.2). Comum aos dois épicos: A cria e edita, B vota e mostra
o resultado.

Espelho TypeScript: `web/src/enquetes/tipos.ts` (conferido por `testes/test_contrato.py`).
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, Field, ValidationInfo, field_validator

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


def validar_pergunta(pergunta: str) -> str:
    sem_invisivel_nenhum(pergunta)
    pergunta = pergunta.strip()
    if not pergunta:
        raise ValueError("Escreva a pergunta.")
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
        opcao = opcao.strip()
        if not opcao:
            continue
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


def validar_encerramento(quando: datetime) -> datetime:
    if quando.tzinfo is None or quando.utcoffset() is None:
        raise ValueError("Informe a hora com o fuso (ex.: -03:00).")
    agora = datetime.now(UTC)
    # O ano vem antes da conta: somar ao ano 9999 estoura o datetime (achado 1 do M1).
    if quando.year > agora.year + 2 or quando > agora + DURACAO_MAXIMA:
        raise ValueError("A enquete pode durar até 1 ano.")
    if quando <= agora:
        raise ValueError("A data de término já passou. Escolha uma data no futuro.")
    if quando < agora + DURACAO_MINIMA:
        raise ValueError("Escolha um término daqui a pelo menos 1 hora.")
    return quando


Pergunta = Annotated[str, AfterValidator(validar_pergunta)]
Opcoes = Annotated[list[str], AfterValidator(validar_opcoes)]
Encerramento = Annotated[datetime, AfterValidator(validar_encerramento)]


# --- requisições -------------------------------------------------------------------------------


class EditarEnquete(Entrada):
    """`PUT /api/enquetes/{id}` (épico A): só enquanto ninguém votou e a enquete está aberta. O
    formulário manda tudo; as opções substituem as anteriores, na ordem. Destino não muda."""

    pergunta: Pergunta
    opcoes: Opcoes
    multipla_escolha: bool = False
    encerra_em: Encerramento
    mostrar_resultado: MostrarResultado = MostrarResultado.durante


class NovaEnquete(EditarEnquete):
    """`POST /api/enquetes` (H-20, épico A). `blocos` só vale quando `para_todos` é falso."""

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

    opcoes: list[IdBanco]

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
