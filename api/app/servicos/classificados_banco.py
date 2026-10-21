"""Os erros do banco dos classificados em resposta da API (no padrão de `indicacoes_banco`).

O banco é a última linha das regras (migração 0011). Quando ele recusa, a rota responde 4xx com
a frase pronta, nunca 500: `traduzir(erro)` devolve o `ErroApi`, ou `None` se o erro não é de
nenhuma regra conhecida (aí é defeito, e o 500 é o certo). `test_classificados_erros_do_banco.py`
confere que toda regra das triggers, toda restrição e todo índice único das quatro tabelas estão
aqui.
"""

import psycopg
from psycopg import errors
from sqlalchemy.exc import DBAPIError

from app.erros_api import MENSAGEM_PADRAO, ErroApi

_CAMPOS = (422, "dados_invalidos", MENSAGEM_PADRAO)
_CONFLITO = (409, "tente_de_novo", "Outra pessoa mexeu neste anúncio agora. Tente de novo.")
_INATIVA = (
    403,
    "unidade_inativa",
    "Este apartamento foi desativado no Portal. Fale com a administração.",
)
_ESCONDIDO = (
    409,
    "anuncio_escondido",
    "A gestão escondeu este anúncio. Ele só pode ser encerrado.",
)
_ENCERRADO = (
    409,
    "anuncio_encerrado",
    "Este anúncio já foi encerrado e não muda mais. Se quiser, anuncie de novo.",
)
_VENCIDO = (
    409,
    "anuncio_vencido",
    "Este anúncio venceu e saiu da lista. Renove para ele voltar, ou encerre.",
)
_FOTO = (422, "foto_invalida", "Uma das fotos não pode ser usada. Envie a foto de novo.")
_CATEGORIA_EXISTE = (409, "categoria_ja_existe", "Já existe uma categoria com esse nome.")

# Nome da regra (trigger com `constraint = ...`), da restrição ou do índice único → resposta.
RESTRICOES: dict[str, tuple[int, str, str]] = {
    # Triggers da 0011.
    "classificado_de_unidade_inativa": _INATIVA,
    "anuncio_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já fez 5 anúncios hoje. Tente de novo amanhã.",
    ),
    "anuncio_limite_abertos": (
        429,
        "limite_de_abertos",
        "Seu apartamento já tem 10 anúncios abertos. Encerre um para anunciar outro.",
    ),
    "anuncio_foto_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já enviou muitas fotos hoje. Tente de novo amanhã.",
    ),
    "aviso_anuncio_limite_dia": (
        429,
        "limite_do_dia",
        "Seu apartamento já avisou a gestão muitas vezes hoje. Tente de novo amanhã.",
    ),
    "anuncio_limite_fotos": (422, "fotos_demais", "O anúncio pode ter até 4 fotos."),
    "anuncio_fixo": _CONFLITO,
    "anuncio_escondido": _ESCONDIDO,
    "anuncio_encerrado": _ENCERRADO,
    "anuncio_vencido": _VENCIDO,
    "anuncio_renovar_cedo": (
        409,
        "renovar_cedo",
        "Dá para renovar quando faltar menos de 7 dias para o anúncio vencer.",
    ),
    "anuncio_foto_fixa": _FOTO,
    "anuncio_foto_descartada": _FOTO,
    "anuncio_foto_de_outra_unidade": _FOTO,
    "anuncio_foto_anuncio_fechado": _ENCERRADO,
    "anuncio_foto_nao_descartada": _CONFLITO,
    "anuncio_escondimento": _CAMPOS,
    "aviso_anuncio_fixo": _CONFLITO,
    # CHECK (a API valida antes; chegar aqui é um caso que escapou).
    "categoria_classificado_nome_tamanho": _CAMPOS,
    "anuncio_tipo": _CAMPOS,
    "anuncio_titulo_tamanho": _CAMPOS,
    "anuncio_descricao_tamanho": _CAMPOS,
    "anuncio_preco": _CAMPOS,
    "anuncio_contato_formato": _CAMPOS,
    "anuncio_situacao": _CAMPOS,
    "anuncio_motivo_encerramento": _CAMPOS,
    "anuncio_encerramento": _CAMPOS,
    "anuncio_foto_chave": _CAMPOS,
    "anuncio_foto_tipo": _CAMPOS,
    "anuncio_foto_bytes": _CAMPOS,
    "anuncio_foto_ordem": _FOTO,
    "anuncio_foto_estado": _FOTO,
    "aviso_anuncio_motivo_tamanho": _CAMPOS,
    # Únicos.
    "categoria_classificado_nome_unico": _CATEGORIA_EXISTE,
    "anuncio_foto_chave_unica": _CONFLITO,
    "aviso_anuncio_aberto": (409, "aviso_ja_enviado", "Você já avisou a gestão."),
    # Chaves primárias.
    "categoria_classificado_pkey": _CONFLITO,
    "anuncio_pkey": _CONFLITO,
    "anuncio_foto_pkey": _CONFLITO,
    "aviso_anuncio_pkey": _CONFLITO,
    # Chaves estrangeiras.
    "anuncio_categoria_id_fkey": (
        422,
        "categoria_inexistente",
        "Essa categoria não existe. Escolha outra.",
    ),
    "anuncio_unidade_id_fkey": _CONFLITO,
    "anuncio_escondido_por_fkey": _CONFLITO,
    "anuncio_foto_anuncio_id_fkey": _CONFLITO,
    "anuncio_foto_unidade_id_fkey": _CONFLITO,
    "aviso_anuncio_anuncio_id_fkey": _CONFLITO,
    "aviso_anuncio_unidade_id_fkey": _CONFLITO,
    "aviso_anuncio_resolvido_por_fkey": _CONFLITO,
}

INDISPONIVEL = (404, "anuncio_indisponivel", "Este anúncio não está mais disponível.")
ESCONDIDO = _ESCONDIDO
ENCERRADO = _ENCERRADO
VENCIDO = _VENCIDO
FOTO = _FOTO


def restricao(erro: DBAPIError) -> str | None:
    causa = erro.orig
    return causa.diag.constraint_name if isinstance(causa, psycopg.Error) else None


def traduzir(erro: DBAPIError) -> ErroApi | None:
    """O `ErroApi` de um erro do banco dos classificados, ou `None` se não é de nenhuma regra."""
    causa = erro.orig
    if isinstance(causa, errors.SerializationFailure | errors.DeadlockDetected):
        return ErroApi(*_CONFLITO)
    if not isinstance(causa, psycopg.Error):
        return None
    resposta = RESTRICOES.get(causa.diag.constraint_name or "")
    return None if resposta is None else ErroApi(*resposta)
