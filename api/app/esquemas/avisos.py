"""Épico C · Avisos, só texto (spec do M1, seção 4.4). Pertence ao épico C.

Espelho TypeScript: `web/src/avisos/tipos.ts`. O texto do aviso é texto com as marcas do
Markdown restrito (`## `, `**`, `- `, `1. `, `> `; spec dos avisos com formatação, seção 3.1):
quem interpreta é o renderizador da tela, que nunca transforma texto em HTML.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, Field, ValidationInfo, field_validator, model_validator

from app.esquemas.comum import Entrada, Saida, UnidadeRef, sem_controle
from app.modelos.avisos import LIMITE_ONDE, LIMITE_TEXTO, LIMITE_TITULO

NumeroDeBloco = Annotated[int, Field(ge=1, le=9)]


def validar_titulo(titulo: str) -> str:
    sem_controle(titulo)
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("Escreva o título do aviso.")
    if len(titulo) > LIMITE_TITULO:
        raise ValueError("O título pode ter até 120 letras.")
    return titulo


def validar_texto(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = sem_controle(texto, permitidos="\n\t").strip()
    if not texto:
        raise ValueError("Escreva o texto do aviso.")
    if len(texto) > LIMITE_TEXTO:
        raise ValueError("O texto pode ter até 10.000 letras.")
    return texto


def validar_onde(onde: str | None) -> str | None:
    """O local do evento: uma linha, como o título. Vazio vira "sem local" (é opcional)."""
    if onde is None:
        return None
    sem_controle(onde)
    onde = onde.strip()
    if not onde:
        return None
    if len(onde) > LIMITE_ONDE:
        raise ValueError("O local pode ter até 120 letras.")
    return onde


def validar_quando(quando: datetime) -> datetime:
    if quando.tzinfo is None or quando.utcoffset() is None:
        raise ValueError("Informe a hora com o fuso (ex.: -03:00).")
    return quando


Titulo = Annotated[str, AfterValidator(validar_titulo)]
Texto = Annotated[str, AfterValidator(validar_texto)]
Onde = Annotated[str | None, AfterValidator(validar_onde)]
Quando = Annotated[datetime, AfterValidator(validar_quando)]
# `?busca=` do mural (texto livre de uma linha, como o título).
Busca = Annotated[str, AfterValidator(sem_controle)]


class Categoria(StrEnum):
    """Do que o aviso trata (spec dos avisos com formatação, seção 2). `geral` é o padrão."""

    geral = "geral"
    obra = "obra"
    reuniao = "reuniao"
    financeiro = "financeiro"
    urgente = "urgente"


class Evento(Entrada):
    """ "Quando / Onde" do aviso que é um evento. `quando` no passado vale (aviso sobre algo que
    já aconteceu é legítimo); `onde` é opcional."""

    quando: Quando
    onde: Onde = None

    @model_validator(mode="before")
    @classmethod
    def _tem_quando(cls, dados: Any) -> Any:
        # Local sem data não é evento: a mensagem diz o que falta (o banco também recusa).
        if isinstance(dados, dict) and dados.get("quando") is None:
            raise ValueError("Escolha o dia e a hora do evento.")
        return dados


# --- requisições -------------------------------------------------------------------------------


class CorrigirAviso(Entrada):
    """`PUT /api/avisos/{id}`: cria a versão seguinte (H-15). Categoria e evento também são da
    versão: omitidos, a versão nova fica `geral` e sem evento (o formulário sempre manda)."""

    titulo: Titulo
    texto: Texto
    categoria: Categoria = Categoria.geral
    evento: Evento | None = None


class NovoAviso(CorrigirAviso):
    """`POST /api/avisos` (H-12). `blocos` só vale quando `para_todos` é falso."""

    para_todos: bool
    # `validate_default`: omitir `blocos` com `para_todos = false` também é recusado.
    blocos: list[NumeroDeBloco] = Field(default=[], validate_default=True)
    fixado: bool = False

    @field_validator("blocos")
    @classmethod
    def _blocos(cls, blocos: list[int], info: ValidationInfo) -> list[int]:
        if info.data.get("para_todos", True):
            return []
        if not blocos:
            raise ValueError("Escolha pelo menos um bloco, ou Todos os blocos.")
        return sorted(set(blocos))


class MudarFixado(Entrada):
    """`PUT /api/avisos/{id}/fixado`."""

    fixado: bool


# --- respostas ---------------------------------------------------------------------------------


class AvisoResumo(Saida):
    id: int
    titulo: str
    # Primeiro parágrafo da versão em vigor, até 200 caracteres.
    resumo: str
    publicado_em: datetime
    # "Comissão", "Administração do Portal", "Síndico" ou "Conselho" (de aviso.publicado_como).
    publicado_por: str
    # Data da versão em vigor quando há mais de uma ("Editado em"), senão nulo.
    editado_em: datetime | None
    fixado: bool
    para_todos: bool
    blocos: list[int]
    arquivado_em: datetime | None
    lido: bool
    # A unidade leu uma versão anterior à atual e ainda não abriu a correção (U1, revisão do M1).
    corrigido_desde_a_leitura: bool
    # Da versão em vigor (migração 0004).
    categoria: Categoria
    # Para a linha do evento no mural ("Sáb, 11/10 · 9h"); nulo se não é evento.
    evento_quando: datetime | None


class VersaoAviso(Saida):
    versao: int
    titulo: str
    texto: str
    criada_em: datetime
    # Cada versão guarda os dela: o "ver como era antes" mostra a categoria e o evento antigos.
    categoria: Categoria
    evento: Evento | None


class ContagemLeitura(Saida):
    """Contagem "Lido por X de Y unidades" (H-16), só para a gestão."""

    lidos: int
    total: int


class AvisoCompleto(AvisoResumo):
    """`GET /api/avisos/{id}` (só lê) e respostas de publicar, corrigir, arquivar e fixar."""

    texto: str
    evento: Evento | None
    # Da mais nova para a mais antiga, sem a em vigor.
    versoes_anteriores: list[VersaoAviso]
    leitura: ContagemLeitura | None


class ListaAvisos(Saida):
    """`GET /api/avisos`: já na ordem do mural (fixados primeiro, depois do mais novo)."""

    itens: list[AvisoResumo]


class ContagemNaoLidos(Saida):
    quantidade: int


class Alcance(Saida):
    """`GET /api/avisos/alcance`: quantas unidades recebem (prévia do H-12)."""

    unidades: int


class DestinoBloco(Saida):
    numero: int
    nome: str


class Destinos(Saida):
    """`GET /api/avisos/destinos`: blocos ativos, para os botões "Bloco N" do formulário.

    Rota a mais do épico C (dúvida 1 de `duvidas-m1-avisos.md`): os blocos são editáveis
    (H-10), então a tela não pode ter os números fixos no código.
    """

    blocos: list[DestinoBloco]


class Leitura(Saida):
    """`GET /api/avisos/{id}/leitura` (H-16)."""

    lidos: int
    total: int
    # Quem não leu, em dois grupos (U5, revisão do M1): a Comissão cobra de jeitos diferentes.
    nao_entraram: list[UnidadeRef]
    entraram_sem_ler: list[UnidadeRef]
