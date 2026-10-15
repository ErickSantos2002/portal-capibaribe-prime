"""Regras de votar e ver o resultado das enquetes (épico B do M4: H-21, H-22). Pertence ao
épico B.

Contrato: `docs/superpowers/specs/m4-contrato.md`, seções 2.6 e 3; spec do épico:
`docs/superpowers/specs/m4-votar.md`. As rotas (`app/rotas/enquetes.py`) só traduzem HTTP. O
banco garante o resto (migração 0008): um voto por unidade, nada de voto depois do prazo nem
fora do destino, voto completo no commit, nada muda na enquete depois do 1º voto.

Quem vê: a gestão vê todas; a unidade comum, as para todos e as do bloco dela. Fora disso, 404
igual a enquete inexistente (H-21).
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, delete, exists, func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.comum import UnidadeRef
from app.esquemas.enquetes import Enquete as EnqueteSaida
from app.esquemas.enquetes import (
    EnqueteResumo,
    MostrarResultado,
    OpcaoEnquete,
    Participacao,
    Votantes,
    Votar,
)
from app.modelos import Bloco, Unidade
from app.modelos.enquetes import Enquete, EnqueteBloco, EnqueteOpcao, Voto, VotoOpcao
from app.seguranca.dependencias import Logado
from app.servicos import enquetes_banco

MSG_SO_UMA = "Nesta enquete, escolha só uma opção."


# --- erros ------------------------------------------------------------------------------------


def nao_encontrada() -> ErroApi:
    # A mesma resposta para a enquete que não existe e para a que não é do bloco da unidade.
    return ErroApi(
        404,
        "enquete_nao_encontrada",
        "Não achamos esta enquete. O link pode estar incompleto, ou ela é de outro bloco.",
    )


def _encerrada() -> ErroApi:
    return ErroApi(
        409,
        "enquete_encerrada",
        "Esta enquete já terminou: o voto não pode mais ser dado nem trocado.",
    )


def _fora_do_destino() -> ErroApi:
    return ErroApi(
        403,
        "fora_do_destino",
        "Esta enquete não é para o seu bloco: seu apartamento não vota nela.",
    )


def _enquete_mudou() -> ErroApi:
    return ErroApi(
        409,
        "enquete_mudou",
        "A enquete mudou agora há pouco. Abra de novo e confira as opções.",
    )


def _votantes_so_no_fim() -> ErroApi:
    return ErroApi(
        409,
        "votantes_so_no_fim",
        "Nesta enquete o resultado aparece durante a votação, então a lista de quem votou só"
        " aparece quando ela terminar (senão daria para saber em quê cada apartamento votou)."
        " Para acompanhar quem falta durante a votação, crie a enquete com o resultado"
        " “só no fim”.",
    )


def _so_uma() -> ErroApi:
    return ErroApi(
        422, "dados_invalidos", MSG_SO_UMA, campos=[{"campo": "opcoes", "mensagem": MSG_SO_UMA}]
    )


# --- consultas --------------------------------------------------------------------------------


def _agora() -> datetime:
    return datetime.now(UTC)


def _do_bloco(numero: int) -> ColumnElement[bool]:
    return exists(
        select(EnqueteBloco.enquete_id)
        .join(Bloco, Bloco.id == EnqueteBloco.bloco_id)
        .where(EnqueteBloco.enquete_id == Enquete.id, Bloco.numero == numero)
    )


def _visivel(logado: Logado) -> ColumnElement[bool]:
    if logado.gestao:
        return true()
    return Enquete.para_todos | _do_bloco(logado.bloco)


def _buscar(db: Session, logado: Logado, enquete_id: int) -> Enquete:
    enquete = db.scalars(
        select(Enquete).where(Enquete.id == enquete_id, _visivel(logado))
    ).one_or_none()
    if enquete is None:
        raise nao_encontrada()
    return enquete


def _blocos(db: Session, ids: Sequence[int]) -> dict[int, list[int]]:
    """Números dos blocos de cada enquete (vazio para as que são para todos)."""
    por_enquete: dict[int, list[int]] = defaultdict(list)
    for enquete_id, numero in db.execute(
        select(EnqueteBloco.enquete_id, Bloco.numero)
        .join(Bloco, Bloco.id == EnqueteBloco.bloco_id)
        .where(EnqueteBloco.enquete_id.in_(ids))
        .order_by(Bloco.numero)
    ):
        por_enquete[enquete_id].append(numero)
    return por_enquete


def _votaram(enquete: Enquete):
    return select(Voto.unidade_id).where(Voto.enquete_id == enquete.id)


def _unidades_do_destino(enquete: Enquete):
    """Ids da base da participação: as unidades do destino ativas agora **ou** que votaram
    (revisão, ponto 2). Quem votou e depois foi desativado continua contando, no "votaram" e no
    total; quem saiu sem votar sai da conta. Assim "votaram" nunca passa do total, o resultado
    de uma enquete terminada não muda (RF-25) e a lista de votantes soma o total."""
    consulta = select(Unidade.id).where(Unidade.ativa | Unidade.id.in_(_votaram(enquete)))
    if not enquete.para_todos:
        consulta = consulta.where(
            Unidade.bloco_id.in_(
                select(EnqueteBloco.bloco_id).where(EnqueteBloco.enquete_id == enquete.id)
            )
        )
    return consulta


def _resumo(enquete: Enquete, blocos: list[int], ja_votou: bool, agora: datetime) -> dict:
    return {
        "id": enquete.id,
        "pergunta": enquete.pergunta,
        "multipla_escolha": enquete.multipla_escolha,
        "mostrar_resultado": MostrarResultado(enquete.mostrar_resultado),
        "encerra_em": enquete.encerra_em,
        "encerrada": enquete.encerra_em <= agora,
        "para_todos": enquete.para_todos,
        "blocos": blocos,
        "criada_em": enquete.criada_em,
        "editada_em": enquete.editada_em,
        "ja_votou": ja_votou,
    }


# --- leitura ----------------------------------------------------------------------------------


def listar(db: Session, logado: Logado) -> list[EnqueteResumo]:
    """Abertas primeiro (a que termina antes no topo), depois as encerradas (a que terminou por
    último no topo); empate pelo id mais novo."""
    agora = _agora()
    enquetes = db.scalars(select(Enquete).where(_visivel(logado)).order_by(Enquete.id.desc())).all()
    ids = [e.id for e in enquetes]
    blocos = _blocos(db, ids)
    votadas = set(
        db.scalars(
            select(Voto.enquete_id).where(
                Voto.enquete_id.in_(ids), Voto.unidade_id == logado.unidade_id
            )
        )
    )
    abertas = sorted((e for e in enquetes if e.encerra_em > agora), key=lambda e: e.encerra_em)
    encerradas = sorted(
        (e for e in enquetes if e.encerra_em <= agora), key=lambda e: e.encerra_em, reverse=True
    )
    # `sorted` é estável: o empate fica na ordem da consulta (id desc).
    return [
        EnqueteResumo(**_resumo(e, blocos.get(e.id, []), e.id in votadas, agora))
        for e in abertas + encerradas
    ]


def _no_destino(enquete: Enquete, blocos: list[int], logado: Logado) -> bool:
    return enquete.para_todos or logado.bloco in blocos


def _montar(db: Session, logado: Logado, enquete: Enquete) -> EnqueteSaida:
    agora = _agora()
    blocos = _blocos(db, [enquete.id]).get(enquete.id, [])
    encerrada = enquete.encerra_em <= agora
    # "Só no fim" (H-22): enquanto aberta, ninguém vê os votos, nem a gestão (dúvida 4).
    visivel = enquete.mostrar_resultado == MostrarResultado.durante or encerrada
    contagem = dict(
        db.execute(
            select(VotoOpcao.opcao_id, func.count())
            .where(VotoOpcao.enquete_id == enquete.id)
            .group_by(VotoOpcao.opcao_id)
        ).all()
    )
    opcoes = [
        OpcaoEnquete(id=o.id, texto=o.texto, votos=contagem.get(o.id, 0) if visivel else None)
        for o in db.scalars(
            select(EnqueteOpcao)
            .where(EnqueteOpcao.enquete_id == enquete.id)
            .order_by(EnqueteOpcao.ordem)
        )
    ]
    votado_em = db.scalar(
        select(Voto.votado_em).where(
            Voto.enquete_id == enquete.id, Voto.unidade_id == logado.unidade_id
        )
    )
    meu_voto = list(
        db.scalars(
            select(VotoOpcao.opcao_id)
            .join(EnqueteOpcao, EnqueteOpcao.id == VotoOpcao.opcao_id)
            .where(VotoOpcao.enquete_id == enquete.id, VotoOpcao.unidade_id == logado.unidade_id)
            .order_by(EnqueteOpcao.ordem)
        )
    )
    destino = _unidades_do_destino(enquete).subquery()
    participacao = Participacao(
        votaram=db.scalar(
            select(func.count()).select_from(destino).where(destino.c.id.in_(_votaram(enquete)))
        )
        or 0,
        total=db.scalar(select(func.count()).select_from(destino)) or 0,
    )
    return EnqueteSaida(
        **_resumo(enquete, blocos, votado_em is not None, agora),
        opcoes=opcoes,
        meu_voto=meu_voto,
        votado_em=votado_em,
        participacao=participacao,
        resultado_visivel=visivel,
        pode_votar=not encerrada and _no_destino(enquete, blocos, logado),
        pode_editar=logado.gestao and not encerrada and enquete.primeiro_voto_em is None,
        aviso_id=enquete.aviso_id,
    )


def abrir(db: Session, logado: Logado, enquete_id: int) -> EnqueteSaida:
    return _montar(db, logado, _buscar(db, logado, enquete_id))


def votantes(db: Session, logado: Logado, enquete_id: int) -> Votantes:
    """Quais apartamentos votaram (H-22), nunca em quê. Sobre a mesma base da participação:
    quem votou e depois foi desativado continua em `votaram`; os três grupos somam o total.

    No "durante", só depois do fim (revisão, ponto 1): com a contagem por opção ao vivo, duas
    olhadas (antes e depois de um apartamento entrar na lista) diriam em quê ele votou."""
    enquete = _buscar(db, logado, enquete_id)
    if enquete.mostrar_resultado == MostrarResultado.durante and enquete.encerra_em > _agora():
        raise _votantes_so_no_fim()
    base = _unidades_do_destino(enquete)
    linhas = db.execute(
        select(Unidade.login, Unidade.ativada_em.is_not(None), Unidade.id.in_(_votaram(enquete)))
        .where(Unidade.id.in_(base))
        .order_by(Unidade.login)
    ).all()
    votaram = [login for login, _, votou in linhas if votou]
    faltam = [(login, entrou) for login, entrou, votou in linhas if not votou]
    return Votantes(
        votaram=[UnidadeRef.de_login(login) for login in votaram],
        entraram_sem_votar=[UnidadeRef.de_login(login) for login, entrou in faltam if entrou],
        nao_entraram=[UnidadeRef.de_login(login) for login, entrou in faltam if not entrou],
    )


# --- votar ------------------------------------------------------------------------------------


def _opcoes_da_enquete(db: Session, enquete_id: int) -> set[int]:
    return set(db.scalars(select(EnqueteOpcao.id).where(EnqueteOpcao.enquete_id == enquete_id)))


def _gravar_voto(db: Session, enquete_id: int, unidade_id: int) -> None:
    """1º passo da gravação (contrato, seção 2.6): o `on conflict do update` trava a linha do
    voto da unidade; outro celular da mesma unidade espera aqui até este terminar."""
    comando = insert(Voto).values(enquete_id=enquete_id, unidade_id=unidade_id)
    db.execute(
        comando.on_conflict_do_update(
            index_elements=["enquete_id", "unidade_id"],
            set_={"votado_em": comando.excluded.votado_em},
        )
    )


def _trocar_opcoes(db: Session, enquete_id: int, unidade_id: int, opcoes: Sequence[int]) -> None:
    """2º e 3º passos: apagar as opções de antes e inserir as novas (o voto anterior não é
    guardado; modelo de dados, seção 3.5)."""
    db.execute(
        delete(VotoOpcao).where(
            VotoOpcao.enquete_id == enquete_id, VotoOpcao.unidade_id == unidade_id
        )
    )
    db.execute(
        insert(VotoOpcao),
        [{"enquete_id": enquete_id, "unidade_id": unidade_id, "opcao_id": o} for o in opcoes],
    )


def votar(db: Session, logado: Logado, enquete_id: int, dados: Votar) -> EnqueteSaida:
    """Votar e trocar o voto (H-21): vale sempre o último. As conferências daqui dão a resposta
    certa no caso comum; o banco confere tudo de novo na gravação (prazo pelo relógio dele,
    destino, opção da enquete, escolha única no commit)."""
    enquete = _buscar(db, logado, enquete_id)
    if enquete.encerra_em <= _agora():
        raise _encerrada()
    if not _no_destino(enquete, _blocos(db, [enquete.id]).get(enquete.id, []), logado):
        raise _fora_do_destino()
    if not set(dados.opcoes) <= _opcoes_da_enquete(db, enquete.id):
        raise _enquete_mudou()
    if not enquete.multipla_escolha and len(dados.opcoes) > 1:
        raise _so_uma()
    try:
        _gravar_voto(db, enquete.id, logado.unidade_id)
        _trocar_opcoes(db, enquete.id, logado.unidade_id, dados.opcoes)
        db.commit()
    except DBAPIError as erro:
        db.rollback()
        traduzido = enquetes_banco.traduzir(erro)
        if traduzido is None:
            raise
        raise traduzido from erro
    db.expire_all()
    return abrir(db, logado, enquete.id)
