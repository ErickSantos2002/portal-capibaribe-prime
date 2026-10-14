"""Regras de criar e editar enquetes (épico A do M4: H-20, com o aviso automático do H-13).
Pertence ao épico A.

Spec: `docs/superpowers/specs/m4-gestao.md`; contrato: `m4-contrato.md`, seção 3.1. A rota
(`app/rotas/enquetes_gestao.py`) só traduz HTTP e agenda a notificação depois do commit. O banco
garante o resto (migração 0008): datas carimbadas, prazo, enquete completa no commit, destino só
na criação e igual ao do aviso, nada muda depois do 1º voto nem depois do encerramento. Quando o
banco recusa, `enquetes_banco.traduzir` dá a resposta (4xx, nunca 500).
"""

from collections.abc import Callable, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.avisos import Categoria, CorrigirAviso, NovoAviso
from app.esquemas.enquetes import EditarEnquete, MostrarResultado, NovaEnquete
from app.modelos import Aviso, AvisoVersao, Bloco, Enquete, EnqueteBloco, EnqueteOpcao
from app.modelos.avisos import LIMITE_TITULO as LIMITE_TITULO_AVISO
from app.seguranca.dependencias import Logado
from app.servicos import avisos, enquetes_banco
from app.servicos.email import FUSO_DE_RECIFE
from app.servicos.historico import Acao, registrar

PREFIXO_DO_AVISO = "Enquete nova: "


def nao_encontrada() -> ErroApi:
    return ErroApi(404, "enquete_nao_encontrada", "Enquete não encontrada.")


# --- o aviso automático (spec do épico, seção 1.2) ----------------------------------------------


def titulo_do_aviso(pergunta: str) -> str:
    completo = PREFIXO_DO_AVISO + pergunta
    if len(completo) <= LIMITE_TITULO_AVISO:
        return completo
    return completo[: LIMITE_TITULO_AVISO - 1].rstrip() + "…"


def texto_do_aviso(dados: EditarEnquete) -> str:
    """O mesmo texto no mural e no e-mail. O front repete esta frase na prévia
    (`web/src/enquetes/gestao/formatos.ts`); os testes dos dois lados conferem."""
    termino = dados.encerra_em.astimezone(FUSO_DE_RECIFE)
    escolha = "Pode marcar mais de uma opção." if dados.multipla_escolha else "Marque uma opção."
    resultado = (
        "O resultado só aparece quando a enquete terminar."
        if dados.mostrar_resultado == MostrarResultado.so_no_fim
        else "O resultado aparece durante a votação."
    )
    lista = "\n".join(f"- {opcao}" for opcao in dados.opcoes)
    return (
        f"Uma enquete nova está aberta no Portal: “{dados.pergunta}”.\n\n"
        f"As opções são:\n\n{lista}\n\n"
        f"Dá para votar até {termino:%d/%m/%Y}, às {termino.hour}h{termino:%M} (horário de"
        f" Recife). {escolha} Vale um voto por apartamento, e dá para trocar o voto até o fim."
        f" {resultado}\n\n"
        "> Enquete é consulta. Não tem valor legal de votação em assembleia.\n\n"
        "O botão “Ir para a enquete”, neste aviso, leva direto a ela."
    )


# --- apoio --------------------------------------------------------------------------------------


def _traduzindo(db: Session, acao: Callable[[], object]) -> None:
    """Roda `flush` ou `commit`; recusa do banco vira a resposta certa e desfaz tudo."""
    try:
        acao()
    except DBAPIError as erro:
        db.rollback()
        traduzido = enquetes_banco.traduzir(erro)
        if traduzido is None:
            raise
        raise traduzido from erro


def _ids_dos_blocos(db: Session, numeros: Sequence[int]) -> list[int]:
    """Já conferidos pelo aviso (`gravar_publicacao`: bloco inexistente é 422 lá)."""
    return list(db.scalars(select(Bloco.id).where(Bloco.ativo, Bloco.numero.in_(numeros))))


def _numeros_dos_blocos(db: Session, enquete_id: int) -> list[int]:
    return list(
        db.scalars(
            select(Bloco.numero)
            .join(EnqueteBloco, EnqueteBloco.bloco_id == Bloco.id)
            .where(EnqueteBloco.enquete_id == enquete_id)
            .order_by(Bloco.numero)
        )
    )


def _detalhes(dados: EditarEnquete, para_todos: bool, blocos: list[int]) -> dict:
    """O que o histórico guarda de `enquete_criada` e `enquete_editada` (contrato, 3.1)."""
    return {
        "pergunta": dados.pergunta,
        "opcoes": len(dados.opcoes),
        "multipla_escolha": dados.multipla_escolha,
        "mostrar_resultado": dados.mostrar_resultado.value,
        "para_todos": para_todos,
        "blocos": [] if para_todos else blocos,
    }


def _gravar_opcoes(db: Session, enquete_id: int, opcoes: Sequence[str]) -> None:
    db.add_all(
        EnqueteOpcao(enquete_id=enquete_id, texto=texto, ordem=ordem)
        for ordem, texto in enumerate(opcoes, start=1)
    )


# --- criar --------------------------------------------------------------------------------------


def criar(db: Session, logado: Logado, dados: NovaEnquete) -> tuple[int, int]:
    """H-20. Devolve (enquete, aviso automático). Os dois nascem na mesma transação, ou nenhum;
    quem chama agenda a notificação do aviso depois do commit."""
    aviso_id = avisos.gravar_publicacao(
        db,
        logado,
        NovoAviso(
            titulo=titulo_do_aviso(dados.pergunta),
            texto=texto_do_aviso(dados),
            categoria=Categoria.geral,
            para_todos=dados.para_todos,
            blocos=dados.blocos,
        ),
    )
    enquete = Enquete(
        pergunta=dados.pergunta,
        multipla_escolha=dados.multipla_escolha,
        mostrar_resultado=dados.mostrar_resultado.value,
        encerra_em=dados.encerra_em,
        para_todos=dados.para_todos,
        criada_por=logado.unidade_id,
        aviso_id=aviso_id,
    )
    db.add(enquete)
    _traduzindo(db, db.flush)
    _gravar_opcoes(db, enquete.id, dados.opcoes)
    if not dados.para_todos:
        db.add_all(
            EnqueteBloco(enquete_id=enquete.id, bloco_id=b)
            for b in _ids_dos_blocos(db, dados.blocos)
        )
    _traduzindo(db, db.flush)
    registrar(
        db,
        Acao.enquete_criada,
        unidade_id=logado.unidade_id,
        entidade="enquete",
        entidade_id=enquete.id,
        detalhes=_detalhes(dados, dados.para_todos, dados.blocos),
    )
    enquete_id = enquete.id
    _traduzindo(db, db.commit)
    return enquete_id, aviso_id


# --- editar -------------------------------------------------------------------------------------


def _corrigir_o_aviso(db: Session, logado: Logado, aviso_id: int, dados: EditarEnquete) -> None:
    """Versão nova do aviso automático, sem notificar (correção nunca notifica). Não corrige se
    o título e o texto ficariam iguais (só os segundos do término mudaram), nem se a gestão
    arquivou o aviso (dúvidas do épico A, item 4)."""
    arquivado = db.scalar(select(Aviso.arquivado_em).where(Aviso.id == aviso_id))
    if arquivado is not None:
        return
    titulo, texto = titulo_do_aviso(dados.pergunta), texto_do_aviso(dados)
    atual = db.execute(
        select(AvisoVersao.titulo, AvisoVersao.texto)
        .where(AvisoVersao.aviso_id == aviso_id)
        .order_by(AvisoVersao.versao.desc())
        .limit(1)
    ).one()
    if (atual.titulo, atual.texto) == (titulo, texto):
        return
    avisos.gravar_correcao(db, logado, aviso_id, CorrigirAviso(titulo=titulo, texto=texto))


def editar(db: Session, logado: Logado, enquete_id: int, dados: EditarEnquete) -> int:
    """Só enquanto ninguém votou e a enquete está aberta. Devolve o aviso automático.

    A trava da linha (`for update`) espera um voto em andamento: quem chega depois vê a coluna
    `primeiro_voto_em` preenchida e recebe 409, nunca passa por baixo do voto."""
    enquete = db.scalars(
        select(Enquete).where(Enquete.id == enquete_id).with_for_update()
    ).one_or_none()
    if enquete is None:
        raise nao_encontrada()
    if enquete.primeiro_voto_em is not None:
        raise ErroApi(*enquetes_banco.RESTRICOES["enquete_com_voto"])
    agora = db.scalar(select(func.clock_timestamp()))
    if agora is not None and enquete.encerra_em <= agora:
        raise ErroApi(*enquetes_banco.RESTRICOES["enquete_encerrada"])
    opcoes_atuais = list(
        db.scalars(
            select(EnqueteOpcao.texto)
            .where(EnqueteOpcao.enquete_id == enquete.id)
            .order_by(EnqueteOpcao.ordem)
        )
    )
    mudou_opcoes = opcoes_atuais != dados.opcoes
    # O término comparado como instante: o mesmo horário em outro fuso não é mudança.
    if not mudou_opcoes and (
        enquete.pergunta,
        enquete.multipla_escolha,
        enquete.mostrar_resultado,
        enquete.encerra_em,
    ) == (dados.pergunta, dados.multipla_escolha, dados.mostrar_resultado.value, dados.encerra_em):
        raise ErroApi(409, "sem_mudanca", "Nada mudou na enquete.")
    # Sempre um UPDATE, mesmo quando só as opções mudaram: o banco carimba `editada_em` e
    # confere de novo voto e prazo (trigger `enquete_regras`).
    aviso_id, para_todos = enquete.aviso_id, enquete.para_todos
    alteracao = (
        update(Enquete)
        .where(Enquete.id == enquete.id)
        .values(
            pergunta=dados.pergunta,
            multipla_escolha=dados.multipla_escolha,
            mostrar_resultado=dados.mostrar_resultado.value,
            encerra_em=dados.encerra_em,
        )
        .execution_options(synchronize_session=False)
    )
    _traduzindo(db, lambda: db.execute(alteracao))
    if mudou_opcoes:
        # Apagar antes de inserir: ordem e texto são únicos na enquete.
        apagar = delete(EnqueteOpcao).where(EnqueteOpcao.enquete_id == enquete_id)
        _traduzindo(db, lambda: db.execute(apagar))
        _gravar_opcoes(db, enquete_id, dados.opcoes)
        _traduzindo(db, db.flush)
    _corrigir_o_aviso(db, logado, aviso_id, dados)
    registrar(
        db,
        Acao.enquete_editada,
        unidade_id=logado.unidade_id,
        entidade="enquete",
        entidade_id=enquete_id,
        detalhes=_detalhes(dados, para_todos, _numeros_dos_blocos(db, enquete_id)),
    )
    _traduzindo(db, db.commit)
    return aviso_id
