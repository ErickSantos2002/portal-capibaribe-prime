"""Os erros do banco das enquetes em resposta da API (spec do M4, seção 3.4). Comum aos dois
épicos: nenhum deles edita, os dois usam.

O banco é a última linha das regras (migração 0008). Quando ele recusa, a rota responde 4xx
com a frase pronta, nunca 500: `traduzir(erro)` devolve o `ErroApi` (e a rota faz
`db.rollback()` e `raise`), ou `None` se o erro não é de nenhuma regra conhecida (aí é defeito,
e o 500 é o certo). `test_m4_erros_do_banco.py` confere que toda regra das triggers e toda
restrição das cinco tabelas estão aqui.
"""

import psycopg
from psycopg import errors
from sqlalchemy.exc import DBAPIError

from app.erros_api import MENSAGEM_PADRAO, ErroApi

_ENCERRADA = (409, "enquete_encerrada", "Esta enquete já terminou. Nada nela muda mais.")
_COM_VOTO = (
    409,
    "enquete_com_voto",
    "A enquete já recebeu votos: a pergunta e as opções não podem mais mudar.",
)
_INCOMPLETA = (
    422,
    "enquete_incompleta",
    "A enquete precisa de 2 a 10 opções e de um destino.",
)
_CAMPOS = (422, "dados_invalidos", MENSAGEM_PADRAO)
_DESTINO = (
    409,
    "destino_invalido",
    "O destino da enquete é o do aviso dela e não muda depois de criada.",
)
_VOTO_MUDOU = (
    409,
    "voto_mudou_agora",
    "O voto do seu apartamento mudou agora há pouco em outro aparelho. Abra de novo e confira.",
)
_ENQUETE_MUDOU = (
    409,
    "enquete_mudou",
    "A enquete mudou agora há pouco. Abra de novo e confira as opções.",
)
_NAO_ENCONTRADA = (404, "enquete_nao_encontrada", "Enquete não encontrada.")
_CONFLITO = (
    409,
    "tente_de_novo",
    "Outra pessoa mexeu nesta enquete agora. Tente de novo.",
)

# Nome da regra (trigger com `constraint = ...`) ou da restrição do Postgres → resposta.
RESTRICOES: dict[str, tuple[int, str, str]] = {
    # Triggers da 0008.
    "enquete_encerrada": _ENCERRADA,
    "enquete_com_voto": _COM_VOTO,
    "enquete_primeiro_voto": _COM_VOTO,
    "enquete_encerramento": (
        422,
        "encerramento_invalido",
        "Escolha um término entre 1 hora e 1 ano a partir de agora.",
    ),
    "enquete_completa": _INCOMPLETA,
    "enquete_opcoes": (422, "enquete_incompleta", "O limite é de 10 opções."),
    "enquete_bloco_destino": _DESTINO,
    "enquete_destino_fechado": _DESTINO,
    "enquete_destino_do_aviso": _DESTINO,
    "voto_fora_do_destino": (403, "fora_do_destino", "Esta enquete não é para o seu bloco."),
    "voto_completo": _VOTO_MUDOU,
    # CHECK e UNIQUE (a API valida antes; chegar aqui é um caso que escapou).
    "enquete_pergunta_tamanho": _CAMPOS,
    "enquete_mostrar_resultado": _CAMPOS,
    "enquete_prazo": (422, "encerramento_invalido", "Escolha um término no futuro."),
    "enquete_opcao_texto_tamanho": _CAMPOS,
    "enquete_opcao_ordem": _CAMPOS,
    "enquete_opcao_ordem_unica": _CAMPOS,
    "enquete_opcao_texto_unico": (422, "opcoes_iguais", "Duas opções estão iguais."),
    "enquete_opcao_da_enquete": _ENQUETE_MUDOU,
    # Chaves primárias e únicas.
    "enquete_pkey": _CONFLITO,
    "enquete_aviso_id_key": _CONFLITO,
    "enquete_opcao_pkey": _CONFLITO,
    "enquete_bloco_pkey": _DESTINO,
    "voto_pkey": _VOTO_MUDOU,
    "voto_opcao_pkey": _VOTO_MUDOU,
    # Chaves estrangeiras.
    "enquete_aviso_id_fkey": _CONFLITO,
    "enquete_criada_por_fkey": _CONFLITO,
    "enquete_opcao_enquete_id_fkey": _NAO_ENCONTRADA,
    "enquete_bloco_enquete_id_fkey": _NAO_ENCONTRADA,
    "enquete_bloco_bloco_id_fkey": (422, "bloco_inexistente", "Esse bloco não existe."),
    "voto_enquete_id_fkey": _NAO_ENCONTRADA,
    "voto_unidade_id_fkey": _CONFLITO,
    "voto_opcao_do_voto": _VOTO_MUDOU,
    "voto_opcao_da_enquete": _ENQUETE_MUDOU,
}


def traduzir(erro: DBAPIError) -> ErroApi | None:
    """O `ErroApi` de um erro do banco das enquetes, ou `None` se não é de nenhuma regra."""
    causa = erro.orig
    if isinstance(causa, errors.SerializationFailure | errors.DeadlockDetected):
        # O Postgres desistiu de uma de duas transações ao mesmo tempo (ex.: editar com a foto
        # de antes de um voto); a outra seguiu. Tentar de novo resolve ou dá a regra certa.
        return ErroApi(*_CONFLITO)
    if not isinstance(causa, psycopg.Error):
        return None
    resposta = RESTRICOES.get(causa.diag.constraint_name or "")
    return None if resposta is None else ErroApi(*resposta)
