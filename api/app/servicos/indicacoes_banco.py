"""Os erros do banco das indicações em resposta da API (no padrão de `enquetes_banco`).

O banco é a última linha das regras (migração 0010). Quando ele recusa, a rota responde 4xx com
a frase pronta, nunca 500: `traduzir(erro)` devolve o `ErroApi` (e a rota faz `db.rollback()` e
`raise`), ou `None` se o erro não é de nenhuma regra conhecida (aí é defeito, e o 500 é o
certo). `test_indicacoes_erros_do_banco.py` confere que toda regra das triggers, toda restrição
e todo índice único das quatro tabelas estão aqui.
"""

import psycopg
from psycopg import errors
from sqlalchemy.exc import DBAPIError

from app.erros_api import MENSAGEM_PADRAO, ErroApi

_CAMPOS = (422, "dados_invalidos", MENSAGEM_PADRAO)
_CONFLITO = (409, "tente_de_novo", "Outra pessoa mexeu nesta indicação agora. Tente de novo.")
_ESCONDIDO = (
    409,
    "prestador_escondido",
    "A gestão tirou este prestador da lista. Ele não recebe mais opiniões nem mudanças.",
)
_OPINIAO_ESCONDIDA = (
    409,
    "opiniao_escondida",
    "A gestão escondeu a sua opinião. Ela não pode ser mudada nem apagada.",
)
_INATIVA = (
    403,
    "unidade_inativa",
    "Este apartamento foi desativado no Portal. Fale com a administração.",
)
_JA_EXISTE = (
    409,
    "prestador_ja_existe",
    "Esse telefone já está na lista. Dê a sua opinião lá.",
)
_CATEGORIA_EXISTE = (409, "categoria_ja_existe", "Já existe uma categoria com esse nome.")
_NAO_ENCONTRADA = (404, "indicacao_nao_encontrada", "Indicação não encontrada.")

# Nome da regra (trigger com `constraint = ...`), da restrição ou do índice único → resposta.
RESTRICOES: dict[str, tuple[int, str, str]] = {
    # Triggers da 0010.
    "indicacao_de_unidade_inativa": _INATIVA,
    "prestador_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já fez muitas indicações hoje. Tente de novo amanhã.",
    ),
    "opiniao_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já deu muitas opiniões hoje. Tente de novo amanhã.",
    ),
    "aviso_servico_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já avisou a gestão muitas vezes hoje. Tente de novo amanhã.",
    ),
    "prestador_escondido": _ESCONDIDO,
    "prestador_autor_fixo": _CONFLITO,
    "opiniao_escondida": _OPINIAO_ESCONDIDA,
    "opiniao_fixa": _CONFLITO,
    "aviso_servico_fixo": _CONFLITO,
    # CHECK (a API valida antes; chegar aqui é um caso que escapou).
    "categoria_servico_nome_tamanho": _CAMPOS,
    "prestador_nome_tamanho": _CAMPOS,
    "prestador_nome_busca": _CAMPOS,
    "prestador_telefone_formato": _CAMPOS,
    "prestador_instagram_formato": _CAMPOS,
    "opiniao_servico_comentario_tamanho": _CAMPOS,
    "aviso_servico_motivo_tamanho": _CAMPOS,
    # Únicos. O telefone repetido tem o id do outro prestador, que só a rota sabe pôr
    # (`indicacoes.erro_de_telefone`); aqui fica a frase.
    "categoria_servico_nome_unico": _CATEGORIA_EXISTE,
    "prestador_telefone_unico": _JA_EXISTE,
    "opiniao_servico_unica": _CONFLITO,
    "aviso_servico_aberto": (409, "aviso_ja_enviado", "Você já avisou a gestão."),
    # Chaves primárias.
    "categoria_servico_pkey": _CONFLITO,
    "prestador_pkey": _CONFLITO,
    "opiniao_servico_pkey": _CONFLITO,
    "aviso_servico_pkey": _CONFLITO,
    # Chaves estrangeiras.
    "prestador_categoria_id_fkey": (
        422,
        "categoria_inexistente",
        "Essa categoria não existe. Escolha outra.",
    ),
    "prestador_criado_por_fkey": _CONFLITO,
    "prestador_escondido_por_fkey": _CONFLITO,
    "opiniao_servico_prestador_id_fkey": _CONFLITO,
    "opiniao_servico_unidade_id_fkey": _CONFLITO,
    "opiniao_servico_escondida_por_fkey": _CONFLITO,
    "aviso_servico_prestador_id_fkey": _CONFLITO,
    "aviso_servico_unidade_id_fkey": _CONFLITO,
    "aviso_servico_resolvido_por_fkey": _CONFLITO,
}

# Usados pelos serviços com a mesma frase.
NAO_ENCONTRADA = _NAO_ENCONTRADA
OPINIAO_ESCONDIDA = _OPINIAO_ESCONDIDA


def restricao(erro: DBAPIError) -> str | None:
    """Nome da regra que o banco recusou, ou `None`."""
    causa = erro.orig
    return causa.diag.constraint_name if isinstance(causa, psycopg.Error) else None


def traduzir(erro: DBAPIError) -> ErroApi | None:
    """O `ErroApi` de um erro do banco das indicações, ou `None` se não é de nenhuma regra."""
    causa = erro.orig
    if isinstance(causa, errors.SerializationFailure | errors.DeadlockDetected):
        return ErroApi(*_CONFLITO)
    if not isinstance(causa, psycopg.Error):
        return None
    resposta = RESTRICOES.get(causa.diag.constraint_name or "")
    return None if resposta is None else ErroApi(*resposta)
