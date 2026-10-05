"""Registro de ações no `historico` (H-11, RNF-14). Função comum que todos os épicos chamam.

O banco garante o resto: o `app` só insere (sem UPDATE nem DELETE) e a data é sempre a do
banco. Aqui se garante que `detalhes` não leva dado pessoal (modelo de dados, seção 3.6).
Não faz commit: a ação e o registro dela vão juntos na transação de quem chama.
"""

import enum
from typing import Any

from sqlalchemy.orm import Session

from app.modelos import Historico
from app.servicos.erros import ErroDoPortal


class Acao(enum.StrEnum):
    # Sistema (M0)
    carga_inicial = "carga_inicial"
    dados_ficticios = "dados_ficticios"
    # Acesso (épico A)
    primeiro_acesso = "primeiro_acesso"
    unidade_bloqueada = "unidade_bloqueada"
    senha_trocada = "senha_trocada"
    dados_apagados = "dados_apagados"
    aparelho_desconectado = "aparelho_desconectado"
    # Administração (épico B)
    unidade_resetada = "unidade_resetada"
    papel_concedido = "papel_concedido"
    papel_retirado = "papel_retirado"
    # Avisos (épico C)
    aviso_publicado = "aviso_publicado"
    aviso_corrigido = "aviso_corrigido"
    aviso_arquivado = "aviso_arquivado"
    aviso_fixado = "aviso_fixado"
    aviso_desafixado = "aviso_desafixado"


# Chaves que denunciam dado pessoal ou segredo. Comparação por "contém", em minúsculas.
_PROIBIDAS = ("senha", "nome", "celular", "telefone", "email", "e_mail", "token", "cpf")
_SIMPLES = (str, int, float, bool, type(None))


def _conferir_detalhes(detalhes: dict[str, Any]) -> None:
    for chave, valor in detalhes.items():
        if any(p in chave.lower() for p in _PROIBIDAS):
            raise ErroDoPortal(f"Detalhe '{chave}' parece dado pessoal: não vai para o histórico.")
        itens = valor if isinstance(valor, list) else [valor]
        if not all(isinstance(i, _SIMPLES) for i in itens):
            raise ErroDoPortal(
                f"Detalhe '{chave}' precisa ser um valor simples (texto, número ou lista deles)."
            )


def registrar(
    db: Session,
    acao: Acao,
    *,
    unidade_id: int | None,
    entidade: str | None = None,
    entidade_id: int | None = None,
    detalhes: dict[str, Any] | None = None,
) -> None:
    """Grava uma linha no histórico. `unidade_id = None` é ação do próprio sistema."""
    detalhes = dict(detalhes or {})
    _conferir_detalhes(detalhes)
    db.add(
        Historico(
            acao=acao.value,
            unidade_id=unidade_id,
            entidade=entidade,
            entidade_id=entidade_id,
            detalhes=detalhes,
        )
    )
    db.flush()
