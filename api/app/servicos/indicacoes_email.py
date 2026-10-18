"""E-mail para a administração no primeiro aviso aberto de uma indicação (spec de 18/10/2026,
seção 8; o mesmo envio em segundo plano dos avisos, ADR-0010).

Ninguém precisa abrir as indicações para moderar: quando chega o **primeiro aviso aberto** de
um prestador, cada unidade com papel `admin` em vigor, ativa e com e-mail recebe um e-mail (a
Comissão também pode esconder, mas não é acordada por isso). Vai mesmo para quem desligou
"receber os avisos por e-mail", que vale para o mural.

Entra na cota do Gmail: em transação própria, com a trava da cota, reserva em
`aviso_servico.emails_reservados` quantos couberem, e manda só esses. Nada aqui levanta para
fora: erro vira log só com o tipo (nem nome do prestador, nem endereço).
"""

import logging
from collections.abc import Callable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.banco import fabrica_de_sessoes
from app.configuracao import config_email
from app.modelos import Papel, Unidade, UnidadePapel
from app.modelos.indicacoes import AvisoServico, CategoriaServico, Prestador
from app.servicos import email, notificacoes

log = logging.getLogger(__name__)


def _destinatarios(db: Session) -> list[str]:
    """E-mails das unidades com papel `admin` em vigor, ativas e com e-mail, por id."""
    return list(
        db.scalars(
            select(Unidade.email)
            .join(UnidadePapel, UnidadePapel.unidade_id == Unidade.id)
            .where(
                UnidadePapel.papel == Papel.admin,
                UnidadePapel.retirado_em.is_(None),
                Unidade.ativa.is_(True),
                Unidade.email.is_not(None),
            )
            .order_by(Unidade.id)
        )
    )


def _reservar(abrir: Callable[[], Session], aviso_id: int) -> tuple[str, str, int, list[str]]:
    """Reserva a cota e devolve o nome e a categoria do prestador, o id dele e para quem mandar
    (só os que couberam). Nada a mandar: lista vazia."""
    with abrir() as db:
        db.execute(select(func.pg_advisory_xact_lock(notificacoes.TRAVA_COTA_EMAIL)))
        linha = db.execute(
            select(Prestador.id, Prestador.nome, CategoriaServico.nome)
            .join(AvisoServico, AvisoServico.prestador_id == Prestador.id)
            .join(CategoriaServico, CategoriaServico.id == Prestador.categoria_id)
            .where(AvisoServico.id == aviso_id)
        ).one_or_none()
        if linha is None:
            db.rollback()
            return "", "", 0, []
        prestador_id, nome, categoria = linha
        para = _destinatarios(db)
        concedidos = min(len(para), notificacoes.cota_email_avisos(db))
        if concedidos > 0:
            db.execute(
                update(AvisoServico)
                .where(AvisoServico.id == aviso_id)
                .values(emails_reservados=AvisoServico.emails_reservados + concedidos)
            )
        db.commit()
    if concedidos < len(para):
        log.warning("aviso de indicação: %d e-mail(s) fora da cota do dia", len(para) - concedidos)
    return nome, categoria, prestador_id, para[:concedidos]


def avisar_administracao(aviso_id: int, fabrica: Callable[[], Session] | None = None) -> None:
    """Depois da resposta de `POST /api/indicacoes/{id}/aviso`. Nunca levanta."""
    try:
        config = config_email()
        if config is None:
            return
        abrir = fabrica or fabrica_de_sessoes()
        nome, categoria, prestador_id, para = _reservar(abrir, aviso_id)
        if not para:
            return
        with email.conexao_smtp(config) as conexao:
            for endereco in para:
                mensagem = email.mensagem_de_aviso_de_indicacao(
                    nome, categoria, prestador_id, endereco, config
                )
                try:
                    conexao.send_message(mensagem)
                except Exception as erro:  # noqa: BLE001 - um destino falhou; os outros seguem
                    log.error("aviso de indicação: um e-mail não saiu (%s)", type(erro).__name__)
    except Exception as erro:  # noqa: BLE001 - depois da resposta ninguém veria a exceção
        log.error("aviso de indicação: e-mail não terminou (%s)", type(erro).__name__)
