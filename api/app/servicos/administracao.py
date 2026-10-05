"""Épico B · Administração: painel de ativação (H-07), reset (H-08), papéis (H-09) e histórico
(H-11). Regras de negócio; as rotas (`app/rotas/administracao.py`) só traduzem HTTP.

Como o resto do projeto, nada aqui faz commit: quem chama decide. Quando o banco recusa (último
admin, papel em unidade não ativada), a transação é desfeita aqui mesmo e sobe um `ErroApi`.

O banco é a última palavra (migração 0002): o último `admin` não sai (`ultimo_admin`), papel só
em unidade ativada (`papel_em_unidade_ativada`) e unidade com papel não volta a "não ativada"
(`unidade_com_papel`, por isso o reset retira os papéis antes).
"""

import re
from typing import Any

import psycopg
from sqlalchemy import Select, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.erros_api import ErroApi
from app.esquemas.administracao import (
    ItemHistorico,
    PaginaHistorico,
    PainelAtivacao,
    PapelGerenciavel,
    ResumoAtivacao,
    ResumoBloco,
    Situacao,
    UnidadeAdmin,
    UnidadePainel,
)
from app.esquemas.comum import UnidadeRef
from app.modelos import AvisoVersao, Bloco, Historico, Papel, Sessao, Unidade, UnidadePapel
from app.seguranca.senhas import SENHA_INICIAL, gerar_hash
from app.seguranca.sessoes import VALIDADE, encerrar_todas
from app.servicos.historico import Acao, registrar

_LOGIN = re.compile(r"^[1-9][0-7][0-9]{2}$")


def _nao_encontrada() -> ErroApi:
    return ErroApi(404, "unidade_nao_encontrada", "Não achamos este apartamento.")


def _ultimo_admin() -> ErroApi:
    return ErroApi(
        409,
        "ultimo_admin",
        "Esta é a única unidade administradora. Dê o papel de administrador a outra unidade antes.",
    )


def _nao_ativada() -> ErroApi:
    return ErroApi(
        409,
        "unidade_nao_ativada",
        "Só dá para dar papel a um apartamento que já entrou no Portal.",
    )


def _restricao(erro: IntegrityError) -> str | None:
    """Nome da restrição que o Postgres recusou (CHECK, índice único ou trigger)."""
    if isinstance(erro.orig, psycopg.Error):
        return erro.orig.diag.constraint_name
    return None


def percentual(parte: int, total: int) -> int:
    """Inteiro mais próximo, meio para cima (0,5% → 1%). Sem unidades, 0."""
    return (parte * 200 + total) // (total * 2) if total else 0


# --- leitura ----------------------------------------------------------------------------------


def _unidade(db: Session, login: str, *, travar: bool = False) -> Unidade:
    """A unidade ativa do login, ou 404 (inexistente, fora do padrão ou desativada)."""
    if not _LOGIN.fullmatch(login):
        raise _nao_encontrada()
    consulta = select(Unidade).where(Unidade.login == login, Unidade.ativa.is_(True))
    if travar:
        # Reset e papéis da mesma unidade ao mesmo tempo: um espera o outro.
        consulta = consulta.with_for_update()
    unidade = db.scalars(consulta).one_or_none()
    if unidade is None:
        raise _nao_encontrada()
    return unidade


def _papeis_em_vigor(db: Session, unidade_id: int) -> list[Papel]:
    return sorted(
        db.scalars(
            select(UnidadePapel.papel).where(
                UnidadePapel.unidade_id == unidade_id, UnidadePapel.retirado_em.is_(None)
            )
        )
    )


def ficha(db: Session, login: str) -> UnidadeAdmin:
    """`GET /api/admin/unidades/{login}`. Aparelhos: só as sessões que ainda valem (mesma regra
    de `buscar_sessao`). A descrição dos aparelhos não aparece: só a própria unidade vê
    (modelo de dados, seção 5)."""
    unidade = _unidade(db, login)
    bloco = db.get_one(Bloco, unidade.bloco_id)
    aparelhos = db.scalar(
        select(func.count())
        .select_from(Sessao)
        .where(
            Sessao.unidade_id == unidade.id,
            Sessao.encerrada_em.is_(None),
            Sessao.ultimo_uso_em > func.now() - VALIDADE,
            Sessao.criada_em >= unidade.senha_trocada_em,
        )
    )
    return UnidadeAdmin(
        unidade=UnidadeRef(login=unidade.login, bloco=bloco.numero, apartamento=unidade.numero),
        andar=unidade.andar,
        ativada=unidade.ativada_em is not None,
        ativada_em=unidade.ativada_em,
        responsavel_nome=unidade.responsavel_nome,
        celular=unidade.celular,
        email=unidade.email,
        papeis=_papeis_em_vigor(db, unidade.id),
        bloqueada_ate=unidade.bloqueada_ate,
        aparelhos_conectados=aparelhos or 0,
    )


def painel(db: Session, situacao: Situacao) -> PainelAtivacao:
    """`GET /api/admin/unidades` (H-07). Só unidades ativas. O resumo (geral e por bloco) é
    sempre do prédio inteiro; `situacao` filtra só a lista."""
    linhas = db.execute(
        select(Unidade, Bloco.numero, Bloco.nome)
        .join(Bloco, Bloco.id == Unidade.bloco_id)
        .where(Unidade.ativa.is_(True))
        .order_by(Unidade.login)
    ).all()
    papeis: dict[int, list[Papel]] = {}
    for unidade_id, papel in db.execute(
        select(UnidadePapel.unidade_id, UnidadePapel.papel)
        .where(UnidadePapel.retirado_em.is_(None))
        .order_by(UnidadePapel.papel)
    ):
        papeis.setdefault(unidade_id, []).append(papel)

    blocos: dict[int, dict[str, Any]] = {}
    unidades: list[UnidadePainel] = []
    for unidade, numero_bloco, nome_bloco in linhas:
        ativada = unidade.ativada_em is not None
        bloco = blocos.setdefault(
            numero_bloco, {"numero": numero_bloco, "nome": nome_bloco, "total": 0, "ativadas": 0}
        )
        bloco["total"] += 1
        bloco["ativadas"] += ativada
        papeis_da_unidade = sorted(papeis.get(unidade.id, []))
        if not _entra_no_filtro(situacao, ativada, bool(papeis_da_unidade)):
            continue
        unidades.append(
            UnidadePainel(
                unidade=UnidadeRef(
                    login=unidade.login, bloco=numero_bloco, apartamento=unidade.numero
                ),
                andar=unidade.andar,
                ativada=ativada,
                ativada_em=unidade.ativada_em,
                responsavel_nome=unidade.responsavel_nome,
                celular=unidade.celular,
                papeis=papeis_da_unidade,
            )
        )

    total = sum(b["total"] for b in blocos.values())
    ativadas = sum(b["ativadas"] for b in blocos.values())
    return PainelAtivacao(
        resumo=ResumoAtivacao(
            total=total, ativadas=ativadas, percentual=percentual(ativadas, total)
        ),
        blocos=[
            ResumoBloco(**b, percentual=percentual(b["ativadas"], b["total"]))
            for _, b in sorted(blocos.items())
        ],
        unidades=unidades,
    )


def _entra_no_filtro(situacao: Situacao, ativada: bool, tem_papel: bool) -> bool:
    match situacao:
        case Situacao.ativadas:
            return ativada
        case Situacao.nao_ativadas:
            return not ativada
        case Situacao.gestao:
            return tem_papel
        case _:
            return True


# --- reset (H-08) -----------------------------------------------------------------------------


def resetar(db: Session, login: str, admin_id: int) -> None:
    """Volta a unidade ao estado inicial (RF-07). Leituras de aviso (e, depois, votos) ficam.

    Ordem obrigatória: retirar os papéis antes de voltar a unidade a "não ativada" (o banco
    recusa o contrário). Se a unidade é o último admin, nada muda e sobe 409 `ultimo_admin`.
    """
    unidade = _unidade(db, login, travar=True)
    try:
        retirados = _retirar_todos(db, unidade.id, admin_id)
        unidade.senha_hash = gerar_hash(SENHA_INICIAL)
        unidade.precisa_trocar_senha = True
        unidade.ativada_em = None
        unidade.responsavel_nome = None
        unidade.celular = None
        unidade.email = None
        unidade.tentativas_falhas = 0
        unidade.bloqueada_ate = None
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        if _restricao(erro) == "ultimo_admin":
            raise _ultimo_admin() from erro
        raise
    # A troca do hash já invalida as sessões no banco (`senha_trocada_em`); aqui elas também
    # ficam marcadas como encerradas.
    encerrar_todas(db, unidade.id)
    registrar(
        db,
        Acao.unidade_resetada,
        unidade_id=admin_id,
        entidade="unidade",
        entidade_id=unidade.id,
        detalhes={"papeis_retirados": [p.value for p in retirados]},
    )


def _retirar_todos(db: Session, unidade_id: int, admin_id: int) -> list[Papel]:
    retirados = []
    for papel in _papeis_em_vigor(db, unidade_id):
        _retirar(db, unidade_id, papel, admin_id, origem="reset")
        retirados.append(papel)
    return retirados


# --- papéis (H-09) ----------------------------------------------------------------------------


def _retirar(
    db: Session, unidade_id: int, papel: Papel, admin_id: int, origem: str | None = None
) -> bool:
    """Retira o papel em vigor (o banco carimba a data). Devolve se havia o que retirar."""
    resultado = db.execute(
        update(UnidadePapel)
        .where(
            UnidadePapel.unidade_id == unidade_id,
            UnidadePapel.papel == papel,
            UnidadePapel.retirado_em.is_(None),
        )
        .values(retirado_em=func.now(), retirado_por=admin_id)
    )
    if not resultado.rowcount:  # type: ignore[attr-defined]
        return False
    detalhes = {"papel": papel.value}
    if origem:
        detalhes["origem"] = origem
    registrar(
        db,
        Acao.papel_retirado,
        unidade_id=admin_id,
        entidade="unidade",
        entidade_id=unidade_id,
        detalhes=detalhes,
    )
    return True


def dar_papel(db: Session, login: str, papel: PapelGerenciavel, admin_id: int) -> None:
    """Concede o papel (idempotente). Só a unidade que já entrou no Portal recebe papel: uma
    conta de gestão com `mudar123` seria tomada por quem conhece o padrão."""
    unidade = _unidade(db, login, travar=True)
    if unidade.ativada_em is None:
        raise _nao_ativada()
    if Papel(papel.value) in _papeis_em_vigor(db, unidade.id):
        return
    try:
        db.add(
            UnidadePapel(unidade_id=unidade.id, papel=Papel(papel.value), concedido_por=admin_id)
        )
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        match _restricao(erro):
            case "papel_em_unidade_ativada":
                raise _nao_ativada() from erro
            case "unidade_papel_em_vigor":
                # Outro pedido igual chegou antes: o papel já está lá.
                return
        raise
    registrar(
        db,
        Acao.papel_concedido,
        unidade_id=admin_id,
        entidade="unidade",
        entidade_id=unidade.id,
        detalhes={"papel": papel.value},
    )


def retirar_papel(db: Session, login: str, papel: PapelGerenciavel, admin_id: int) -> None:
    """Retira o papel (idempotente). O último admin não sai: 409 `ultimo_admin`."""
    unidade = _unidade(db, login, travar=True)
    try:
        _retirar(db, unidade.id, Papel(papel.value), admin_id)
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        if _restricao(erro) == "ultimo_admin":
            raise _ultimo_admin() from erro
        raise


# --- histórico (H-11) -------------------------------------------------------------------------


def _consulta_historico(antes_de: int | None, limite: int) -> Select:
    autor = aliased(Unidade)
    autor_bloco = aliased(Bloco)
    alvo = aliased(Unidade)
    alvo_bloco = aliased(Bloco)
    # Título da versão em vigor do aviso (a maior). Título de aviso não é dado pessoal.
    titulo = (
        select(AvisoVersao.titulo)
        .where(Historico.entidade == "aviso", AvisoVersao.aviso_id == Historico.entidade_id)
        .order_by(AvisoVersao.versao.desc())
        .limit(1)
        .correlate(Historico)
        .scalar_subquery()
    )
    consulta = (
        select(
            Historico,
            autor.login,
            autor.numero,
            autor_bloco.numero,
            alvo.login,
            alvo.numero,
            alvo_bloco.numero,
            titulo,
        )
        .outerjoin(autor, autor.id == Historico.unidade_id)
        .outerjoin(autor_bloco, autor_bloco.id == autor.bloco_id)
        .outerjoin(alvo, (Historico.entidade == "unidade") & (alvo.id == Historico.entidade_id))
        .outerjoin(alvo_bloco, alvo_bloco.id == alvo.bloco_id)
        .order_by(Historico.id.desc())
        .limit(limite + 1)
    )
    if antes_de is not None:
        consulta = consulta.where(Historico.id < antes_de)
    return consulta


def _ref(login: str | None, apartamento: str | None, bloco: int | None) -> UnidadeRef | None:
    if login is None or apartamento is None or bloco is None:
        return None
    return UnidadeRef(login=login, bloco=bloco, apartamento=apartamento)


def historico(db: Session, antes_de: int | None, limite: int) -> PaginaHistorico:
    """Mais novo primeiro (o `id` cresce com o tempo). Busca um a mais para saber se há
    próxima página."""
    linhas = db.execute(_consulta_historico(antes_de, limite)).all()
    itens = [
        ItemHistorico(
            id=h.id,
            ocorrido_em=h.ocorrido_em,
            unidade=_ref(autor_login, autor_apto, autor_bloco),
            acao=h.acao,
            entidade=h.entidade,
            entidade_id=h.entidade_id,
            unidade_afetada=_ref(alvo_login, alvo_apto, alvo_bloco),
            aviso_titulo=titulo,
            detalhes=h.detalhes,
        )
        for (
            h,
            autor_login,
            autor_apto,
            autor_bloco,
            alvo_login,
            alvo_apto,
            alvo_bloco,
            titulo,
        ) in linhas[:limite]
    ]
    proximo = itens[-1].id if len(linhas) > limite else None
    return PaginaHistorico(itens=itens, proximo=proximo)
