"""Registro de ações no `historico` (H-11, RNF-14). Função comum que todos os épicos chamam.

O banco garante o resto: o `app` só insere (sem UPDATE nem DELETE) e a data é sempre a do
banco. Aqui se garante que `detalhes` não leva dado pessoal (modelo de dados, seção 3.6).
Não faz commit: a ação e o registro dela vão juntos na transação de quem chama.
"""

import enum
from datetime import timedelta
from typing import Any

from sqlalchemy import exists, func, select
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
    # Esqueci a senha (M2, épico B; spec do M2, seção 4.3). O pedido é ação do sistema
    # (`unidade_id` nulo, entidade `unidade`), com `{"enviado": bool, "motivo": ...}`.
    recuperacao_pedida = "recuperacao_pedida"
    senha_redefinida = "senha_redefinida"
    # Envio de arquivo (M3, comum; spec do M3, seção 4): entidade `arquivo`, com
    # `{"motivo": "conteudo" | "tamanho", "finalidade", "tipo_declarado", "tipo_encontrado",
    # "tamanho_bytes"}`, nunca o nome do arquivo.
    arquivo_recusado = "arquivo_recusado"
    # Documentos (M3, épico A; spec do M3, seção 5.2): entidade `documento`.
    documento_publicado = "documento_publicado"
    documento_versao_enviada = "documento_versao_enviada"
    documento_arquivado = "documento_arquivado"
    # Enquetes (M4, épico A; spec do M4, seção 3.1): entidade `enquete`, com `{"pergunta",
    # "opcoes": n, "multipla_escolha", "mostrar_resultado", "para_todos", "blocos"}`. O voto não
    # vai para o histórico (dado sobre o comportamento das pessoas, sem uso).
    enquete_criada = "enquete_criada"
    enquete_editada = "enquete_editada"
    # Indicações de serviços (spec de 18/10/2026, seção 4): entidade `prestador`, sem o nome
    # dele. `indicacao_opiniao_escondida` leva `{"opiniao": id}`; `indicacao_opiniao_apagada`
    # (a própria unidade) conta no limite de opiniões do dia (trigger da 0010).
    indicacao_escondida = "indicacao_escondida"
    indicacao_opiniao_escondida = "indicacao_opiniao_escondida"
    indicacao_opiniao_apagada = "indicacao_opiniao_apagada"
    indicacao_aviso_resolvido = "indicacao_aviso_resolvido"
    # Categorias das indicações (administração): entidade `categoria_servico`, com
    # `{"categoria": nome}` (a chave `nome` é proibida).
    categoria_criada = "categoria_criada"
    categoria_renomeada = "categoria_renomeada"


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


def registrado_recentemente(
    db: Session, acao: Acao, *, entidade: str, entidade_id: int, janela: timedelta
) -> bool:
    """Já há registro desta ação para esta entidade dentro da `janela`? Para ações que alguém de
    fora pode disparar à vontade (o pedido de recuperação, M2) não encherem o histórico."""
    return bool(
        db.scalar(
            select(
                exists().where(
                    Historico.acao == acao.value,
                    Historico.entidade == entidade,
                    Historico.entidade_id == entidade_id,
                    Historico.ocorrido_em > func.now() - janela,
                )
            )
        )
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
