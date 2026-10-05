"""Épico C · Avisos, só texto (spec do M1, seção 4.4). Pertence ao épico C.

Espelho TypeScript: `web/src/avisos/tipos.ts`. Texto do aviso é texto puro com quebras de
linha: a tela nunca interpreta HTML (arquitetura, seção 4).
"""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field, ValidationInfo, field_validator

from app.esquemas.comum import Entrada, Saida, UnidadeRef, sem_controle
from app.modelos.avisos import LIMITE_TEXTO, LIMITE_TITULO

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


Titulo = Annotated[str, AfterValidator(validar_titulo)]
Texto = Annotated[str, AfterValidator(validar_texto)]
# `?busca=` do mural (texto livre de uma linha, como o título).
Busca = Annotated[str, AfterValidator(sem_controle)]


# --- requisições -------------------------------------------------------------------------------


class CorrigirAviso(Entrada):
    """`PUT /api/avisos/{id}`: cria a versão seguinte (H-15)."""

    titulo: Titulo
    texto: Texto


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


class VersaoAviso(Saida):
    versao: int
    titulo: str
    texto: str
    criada_em: datetime


class ContagemLeitura(Saida):
    """Contagem "Lido por X de Y unidades" (H-16), só para a gestão."""

    lidos: int
    total: int


class AvisoCompleto(AvisoResumo):
    """`GET /api/avisos/{id}` (só lê) e respostas de publicar, corrigir, arquivar e fixar."""

    texto: str
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
    nao_leram: list[UnidadeRef]
