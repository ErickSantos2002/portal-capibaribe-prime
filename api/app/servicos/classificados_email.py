"""E-mail para a administração no primeiro aviso aberto de um anúncio (spec de 20/10/2026, seção
9; o mesmo desenho de `indicacoes_email.py` e o envio em segundo plano da ADR-0010).

Cada unidade com papel `admin` em vigor, ativa e com e-mail recebe um e-mail com o título e a
categoria do anúncio e o link, sem o motivo e sem a placa de quem avisou. A cota do Gmail é
reservada no histórico (`classificado_aviso_email`, que ninguém apaga), com a trava da cota.
Nada aqui levanta para fora: erro vira log só com o tipo.
"""

import logging
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.banco import fabrica_de_sessoes
from app.configuracao import config_email
from app.modelos.classificados import Anuncio, AvisoAnuncio, CategoriaClassificado
from app.servicos import email, notificacoes
from app.servicos.historico import Acao, registrar
from app.servicos.indicacoes_email import destinatarios_da_administracao

log = logging.getLogger(__name__)


def _reservar(abrir: Callable[[], Session], aviso_id: int) -> tuple[str, str, int, list[str]]:
    with abrir() as db:
        db.execute(select(func.pg_advisory_xact_lock(notificacoes.TRAVA_COTA_EMAIL)))
        linha = db.execute(
            select(Anuncio.id, Anuncio.titulo, CategoriaClassificado.nome)
            .join(AvisoAnuncio, AvisoAnuncio.anuncio_id == Anuncio.id)
            .join(CategoriaClassificado, CategoriaClassificado.id == Anuncio.categoria_id)
            .where(AvisoAnuncio.id == aviso_id)
        ).one_or_none()
        if linha is None:
            db.rollback()
            return "", "", 0, []
        anuncio_id, titulo, categoria = linha
        para = destinatarios_da_administracao(db)
        concedidos = min(len(para), notificacoes.cota_email_avisos(db))
        if concedidos > 0:
            registrar(
                db,
                Acao.classificado_aviso_email,
                unidade_id=None,
                entidade="anuncio",
                entidade_id=anuncio_id,
                detalhes={"reservados": concedidos},
            )
        db.commit()
    if concedidos < len(para):
        log.warning("aviso de anúncio: %d e-mail(s) fora da cota do dia", len(para) - concedidos)
    return titulo, categoria, anuncio_id, para[:concedidos]


def avisar_administracao(aviso_id: int, fabrica: Callable[[], Session] | None = None) -> None:
    """Depois da resposta de `POST /api/classificados/{id}/aviso`. Nunca levanta."""
    try:
        config = config_email()
        if config is None:
            return
        abrir = fabrica or fabrica_de_sessoes()
        titulo, categoria, anuncio_id, para = _reservar(abrir, aviso_id)
        if not para:
            return
        with email.conexao_smtp(config) as conexao:
            for endereco in para:
                mensagem = email.mensagem_de_aviso_de_classificado(
                    titulo, categoria, anuncio_id, endereco, config
                )
                try:
                    conexao.send_message(mensagem)
                except Exception as erro:  # noqa: BLE001 - um destino falhou; os outros seguem
                    log.error("aviso de anúncio: um e-mail não saiu (%s)", type(erro).__name__)
    except Exception as erro:  # noqa: BLE001 - depois da resposta ninguém veria a exceção
        log.error("aviso de anúncio: e-mail não terminou (%s)", type(erro).__name__)
