"""Épico B · Administração (spec do M1, seção 4.3). Pertence ao épico B.

Espelho TypeScript: `web/src/administracao/tipos.ts`.
"""

import enum
from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.esquemas.comum import Entrada, Papel, Saida, UnidadeRef


class Situacao(enum.StrEnum):
    """Filtro do painel de ativação (H-07)."""

    todas = "todas"
    ativadas = "ativadas"
    nao_ativadas = "nao_ativadas"
    gestao = "gestao"


class PapelGerenciavel(enum.StrEnum):
    """Papéis que o admin dá e retira no M1 (H-09). Síndico e conselho entram na E2."""

    comissao = "comissao"
    admin = "admin"


class ConfirmarReset(Entrada):
    """`POST /api/admin/unidades/{login}/resetar`: `{"confirmo": true}` (H-08)."""

    confirmo: bool

    @field_validator("confirmo")
    @classmethod
    def _confirmo(cls, confirmo: bool) -> bool:
        if confirmo is not True:
            raise ValueError("Confirme o reset do apartamento.")
        return confirmo


class ResumoAtivacao(Saida):
    total: int
    ativadas: int
    percentual: int


class ResumoBloco(Saida):
    numero: int
    nome: str
    total: int
    ativadas: int
    percentual: int


class UnidadePainel(Saida):
    unidade: UnidadeRef
    andar: int
    ativada: bool
    ativada_em: datetime | None
    responsavel_nome: str | None
    celular: str | None
    papeis: list[Papel]


class PainelAtivacao(Saida):
    """`GET /api/admin/unidades` (H-07). O resumo é sempre do prédio inteiro."""

    resumo: ResumoAtivacao
    blocos: list[ResumoBloco]
    unidades: list[UnidadePainel]


class UnidadeAdmin(Saida):
    """`GET /api/admin/unidades/{login}` e respostas de reset e papel (H-08, H-09)."""

    unidade: UnidadeRef
    andar: int
    ativada: bool
    ativada_em: datetime | None
    responsavel_nome: str | None
    celular: str | None
    email: str | None
    papeis: list[Papel]
    bloqueada_ate: datetime | None
    aparelhos_conectados: int


class ItemHistorico(Saida):
    id: int
    ocorrido_em: datetime
    # Nulo = ação do próprio Portal (ex.: bloqueio automático).
    unidade: UnidadeRef | None
    acao: str
    entidade: str | None
    entidade_id: int | None
    # O item afetado, para a tela escrever "resetou o Bloco 1, 106" (H-11). Mudança do épico B
    # no contrato: `duvidas-m1-administracao.md`, item 1.
    unidade_afetada: UnidadeRef | None
    aviso_titulo: str | None
    detalhes: dict[str, Any]


class PaginaHistorico(Saida):
    """`GET /api/admin/historico` (H-11). Mais novo primeiro; `proximo` vai em `antes_de`."""

    itens: list[ItemHistorico]
    proximo: int | None
