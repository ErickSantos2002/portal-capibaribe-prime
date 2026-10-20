"""Modelos SQLAlchemy das tabelas da E1 (`docs/04-modelo-de-dados.md`).

As tabelas nascem pela migração escrita à mão em `migracoes/` (com triggers e permissões que o
ORM não descreve). Estes modelos espelham as colunas para a API ler e gravar.
"""

from app.modelos.acesso import Bloco, EntradaTentativa, Papel, Sessao, Unidade, UnidadePapel
from app.modelos.arquivos import Arquivo
from app.modelos.avisos import Aviso, AvisoAnexo, AvisoBloco, AvisoLeitura, AvisoVersao
from app.modelos.base import Base
from app.modelos.classificados import Anuncio, AnuncioFoto, AvisoAnuncio, CategoriaClassificado
from app.modelos.documentos import Documento, DocumentoVersao
from app.modelos.enquetes import Enquete, EnqueteBloco, EnqueteOpcao, Voto, VotoOpcao
from app.modelos.indicacoes import AvisoServico, CategoriaServico, OpiniaoServico, Prestador
from app.modelos.notificacoes import (
    Canal,
    InscricaoPush,
    NotificacaoEnvio,
    SituacaoEnvio,
    TokenRecuperacao,
)
from app.modelos.registro import Erro, Historico

__all__ = [
    "Anuncio",
    "AnuncioFoto",
    "Arquivo",
    "Aviso",
    "AvisoAnexo",
    "AvisoAnuncio",
    "AvisoBloco",
    "AvisoLeitura",
    "AvisoServico",
    "AvisoVersao",
    "Base",
    "Bloco",
    "Canal",
    "CategoriaClassificado",
    "CategoriaServico",
    "Documento",
    "DocumentoVersao",
    "Enquete",
    "EnqueteBloco",
    "EnqueteOpcao",
    "EntradaTentativa",
    "Erro",
    "Historico",
    "InscricaoPush",
    "NotificacaoEnvio",
    "OpiniaoServico",
    "Papel",
    "Prestador",
    "Sessao",
    "SituacaoEnvio",
    "TokenRecuperacao",
    "Unidade",
    "UnidadePapel",
    "Voto",
    "VotoOpcao",
]
