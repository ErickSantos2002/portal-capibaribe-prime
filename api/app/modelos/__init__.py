"""Modelos SQLAlchemy das tabelas da E1 (`docs/04-modelo-de-dados.md`).

As tabelas nascem pela migração escrita à mão em `migracoes/` (com triggers e permissões que o
ORM não descreve). Estes modelos espelham as colunas para a API ler e gravar.
"""

from app.modelos.acesso import Bloco, Papel, Sessao, Unidade, UnidadePapel
from app.modelos.avisos import Aviso, AvisoBloco, AvisoLeitura, AvisoVersao
from app.modelos.base import Base
from app.modelos.registro import Erro, Historico

__all__ = [
    "Aviso",
    "AvisoBloco",
    "AvisoLeitura",
    "AvisoVersao",
    "Base",
    "Bloco",
    "Erro",
    "Historico",
    "Papel",
    "Sessao",
    "Unidade",
    "UnidadePapel",
]
