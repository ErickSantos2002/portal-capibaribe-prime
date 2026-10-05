"""Senhas em Argon2id, com os parâmetros padrão da biblioteca (ADR-0005).

Os testes trocam `_hasher` por um de custo baixo (fixture `hasher_rapido` do conftest); o código
de produção sempre passa por estas funções, nunca cria o próprio `PasswordHasher`.
"""

from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Pública por decisão (ADR-0005): a troca é obrigatória no primeiro acesso.
SENHA_INICIAL = "mudar123"

_hasher = PasswordHasher()


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def senha_confere(senha_hash: str, senha: str) -> bool:
    """Nunca levanta: hash inválido ou senha errada dão `False`."""
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@cache
def _hash_de_referencia(parametros: str) -> str:
    # Um hash qualquer, com os mesmos parâmetros do hasher em uso (o cache é por parâmetros).
    return _hasher.hash("referencia-para-gastar-o-mesmo-tempo")


def conferir_sem_unidade(senha: str) -> bool:
    """Para login inexistente: gasta o mesmo tempo de uma conferência de verdade e dá `False`.

    Assim o tempo de resposta não separa "unidade não existe" de "senha errada" (H-02).
    """
    parametros = f"{_hasher.time_cost}-{_hasher.memory_cost}-{_hasher.parallelism}"
    senha_confere(_hash_de_referencia(parametros), senha)
    return False
