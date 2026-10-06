"""Modelos SQLAlchemy das tabelas da E1 (`docs/04-modelo-de-dados.md`).

As tabelas nascem pela migração escrita à mão em `migracoes/` (com triggers e permissões que o
ORM não descreve). Estes modelos espelham as colunas para a API ler e gravar.
"""

from app.modelos.acesso import Bloco, EntradaTentativa, Papel, Sessao, Unidade, UnidadePapel
from app.modelos.avisos import Aviso, AvisoBloco, AvisoLeitura, AvisoVersao
from app.modelos.base import Base
from app.modelos.notificacoes import (
    Canal,
    InscricaoPush,
    NotificacaoEnvio,
    SituacaoEnvio,
    TokenRecuperacao,
)
from app.modelos.registro import Erro, Historico

__all__ = [
    "Aviso",
    "AvisoBloco",
    "AvisoLeitura",
    "AvisoVersao",
    "Base",
    "Bloco",
    "Canal",
    "EntradaTentativa",
    "Erro",
    "Historico",
    "InscricaoPush",
    "NotificacaoEnvio",
    "Papel",
    "Sessao",
    "SituacaoEnvio",
    "TokenRecuperacao",
    "Unidade",
    "UnidadePapel",
]
