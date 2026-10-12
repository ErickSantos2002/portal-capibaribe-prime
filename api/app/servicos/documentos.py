"""Regras dos documentos (épico A do M3: H-17, H-18, H-19, RF-33). Pertence ao épico A.

Spec: `docs/superpowers/specs/m3-documentos.md`; contrato: `m3-contrato.md`, seção 5.2. As rotas
(`app/rotas/documentos.py`) só traduzem HTTP. O banco garante o resto (migração 0007): datas
carimbadas, versões em sequência, documento completo no commit, arquivo confirmado e usado uma
vez só, arquivado não volta nem ganha versão.

Quem vê o quê: `niveis_que_ve` (sem sessão, só `publico`) e, se arquivado, só a gestão. Fora
disso, 404 igual a documento inexistente, na lista, no documento e no link.
"""

from collections import defaultdict
from collections.abc import Sequence

import psycopg
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.arquivos import LinkDoArquivo
from app.esquemas.avisos import NovoAviso
from app.esquemas.documentos import Documento as DocumentoSaida
from app.esquemas.documentos import (
    DocumentoResumo,
    NovaVersaoDocumento,
    NovoDocumento,
    VersaoDocumento,
)
from app.modelos import Arquivo, Documento, DocumentoVersao
from app.modelos.avisos import LIMITE_TITULO as LIMITE_TITULO_AVISO
from app.seguranca.dependencias import Logado
from app.servicos import avisos
from app.servicos.armazenamento import Armazenamento
from app.servicos.arquivos import arquivo_utilizavel, como_enviado, link_do_arquivo
from app.servicos.historico import Acao, registrar
from app.servicos.visibilidade import niveis_que_ve

MSG_ENVIE_DE_NOVO = "Envie o arquivo de novo."
PREFIXO_DO_AVISO = "Documento novo: "


# --- erros ------------------------------------------------------------------------------------


def nao_encontrado() -> ErroApi:
    return ErroApi(
        404,
        "documento_nao_encontrado",
        "Não achamos este documento. O link pode estar incompleto, ou ele não está mais"
        " disponível.",
    )


def _envie_de_novo() -> ErroApi:
    return ErroApi(
        422,
        "arquivo_invalido",
        MSG_ENVIE_DE_NOVO,
        campos=[{"campo": "arquivo_id", "mensagem": MSG_ENVIE_DE_NOVO}],
    )


def _arquivado() -> ErroApi:
    return ErroApi(409, "documento_arquivado", "Documento arquivado não recebe versão nova.")


def _em_uso() -> ErroApi:
    return ErroApi(
        409,
        "arquivo_em_uso",
        "Este arquivo já está em outro documento. Escolha o arquivo de novo.",
    )


def _traduzir(erro: IntegrityError) -> ErroApi | None:
    """As restrições do banco que a pessoa pode encontrar (a última linha de defesa)."""
    causa = erro.orig
    restricao = causa.diag.constraint_name if isinstance(causa, psycopg.Error) else None
    if restricao in ("arquivo_em_uso", "documento_versao_arquivo_id_key"):
        return _em_uso()
    if restricao in ("arquivo_nao_confirmado", "arquivo_finalidade_errada"):
        return _envie_de_novo()
    if restricao == "documento_arquivado":
        return _arquivado()
    return None


# --- consultas --------------------------------------------------------------------------------


def _visivel(logado: Logado | None) -> ColumnElement[bool]:
    """O nível que a unidade vê e, arquivado, só para a gestão."""
    filtro = Documento.acesso.in_(niveis_que_ve(logado))
    if logado is None or not logado.gestao:
        filtro = filtro & Documento.arquivado_em.is_(None)
    return filtro


def _versoes(db: Session, ids: Sequence[int]) -> dict[int, list[tuple[DocumentoVersao, Arquivo]]]:
    """Versões (com o arquivo) de cada documento, da mais nova para a mais antiga."""
    versoes: dict[int, list[tuple[DocumentoVersao, Arquivo]]] = defaultdict(list)
    linhas = db.execute(
        select(DocumentoVersao, Arquivo)
        .join(Arquivo, Arquivo.id == DocumentoVersao.arquivo_id)
        .where(DocumentoVersao.documento_id.in_(ids))
        .order_by(DocumentoVersao.documento_id, DocumentoVersao.versao.desc())
    ).all()
    for versao, arquivo in linhas:
        versoes[versao.documento_id].append((versao, arquivo))
    return versoes


def _resumo(documento: Documento, versoes: list[tuple[DocumentoVersao, Arquivo]]) -> dict:
    atual, arquivo = versoes[0]
    return {
        "id": documento.id,
        "titulo": documento.titulo,
        "categoria": documento.categoria,
        "data_documento": documento.data_documento,
        "acesso": documento.acesso,
        "versao": atual.versao,
        "atualizado_em": atual.enviada_em,
        "arquivo": como_enviado(arquivo),
        "arquivado_em": documento.arquivado_em,
    }


def _lista(db: Session, filtro: ColumnElement[bool]) -> list[DocumentoResumo]:
    documentos = db.scalars(
        select(Documento)
        .where(filtro)
        .order_by(Documento.data_documento.desc(), Documento.id.desc())
    ).all()
    versoes = _versoes(db, [d.id for d in documentos])
    return [DocumentoResumo(**_resumo(d, versoes[d.id])) for d in documentos]


def listar(db: Session, logado: Logado, *, arquivados: bool = False) -> list[DocumentoResumo]:
    """H-18. Os arquivados só existem para a gestão; para a unidade comum, lista vazia."""
    if arquivados and not logado.gestao:
        return []
    situacao = (
        Documento.arquivado_em.is_not(None) if arquivados else Documento.arquivado_em.is_(None)
    )
    return _lista(db, _visivel(logado) & situacao)


def publicos(db: Session) -> list[DocumentoResumo]:
    """Os de nível público, para a tela de entrada (sem sessão)."""
    return _lista(db, _visivel(None))


def _buscar(
    db: Session, logado: Logado | None, documento_id: int, *, travar: bool = False
) -> Documento:
    consulta = select(Documento).where(Documento.id == documento_id, _visivel(logado))
    if travar:
        consulta = consulta.with_for_update()
    documento = db.scalars(consulta).one_or_none()
    if documento is None:
        raise nao_encontrado()
    return documento


def _completo(db: Session, documento: Documento) -> DocumentoSaida:
    versoes = _versoes(db, [documento.id])[documento.id]
    return DocumentoSaida(
        **_resumo(documento, versoes),
        versoes_anteriores=[
            VersaoDocumento(versao=v.versao, enviada_em=v.enviada_em, arquivo=como_enviado(a))
            for v, a in versoes[1:]
        ],
        aviso_id=documento.aviso_id,
    )


def abrir(db: Session, logado: Logado, documento_id: int) -> DocumentoSaida:
    return _completo(db, _buscar(db, logado, documento_id))


def link(
    db: Session,
    logado: Logado | None,
    documento_id: int,
    versao: int,
    armazenamento: Armazenamento | None,
    *,
    baixar: bool,
) -> LinkDoArquivo:
    """O link curto do arquivo de uma versão (a atual ou uma anterior), se a unidade vê o
    documento; senão 404, igual ao inexistente."""
    arquivo = db.scalars(
        select(Arquivo)
        .join(DocumentoVersao, DocumentoVersao.arquivo_id == Arquivo.id)
        .join(Documento, Documento.id == DocumentoVersao.documento_id)
        .where(
            Documento.id == documento_id,
            DocumentoVersao.versao == versao,
            _visivel(logado),
        )
    ).one_or_none()
    if arquivo is None:
        raise nao_encontrado()
    return link_do_arquivo(armazenamento, arquivo, baixar=baixar)


# --- gestão -----------------------------------------------------------------------------------


def _arquivo(db: Session, logado: Logado, arquivo_id: int) -> Arquivo:
    arquivo = arquivo_utilizavel(db, logado, arquivo_id, "documento")
    if arquivo is None:
        raise _envie_de_novo()
    return arquivo


def _titulo_do_aviso(titulo: str) -> str:
    completo = PREFIXO_DO_AVISO + titulo
    if len(completo) <= LIMITE_TITULO_AVISO:
        return completo
    return completo[: LIMITE_TITULO_AVISO - 1].rstrip() + "…"


def _aviso_automatico(titulo: str) -> NovoAviso:
    """RF-33. O mesmo texto serve no mural e no e-mail (onde não há "o botão aqui embaixo")."""
    return NovoAviso(
        titulo=_titulo_do_aviso(titulo),
        texto=(
            f"Um documento novo foi publicado no Portal: “{titulo}”.\n\n"
            "Para ver, abra este aviso no Portal e toque em “Abrir o documento”. Ele também"
            " fica guardado em Documentos."
        ),
        para_todos=True,
    )


def _gravar(db: Session) -> None:
    """Flush que traduz as restrições do banco; qualquer erro desfaz tudo."""
    try:
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        traduzido = _traduzir(erro)
        if traduzido is None:
            raise
        raise traduzido from erro


def publicar(db: Session, logado: Logado, dados: NovoDocumento) -> tuple[int, int | None]:
    """H-17. Devolve (documento, aviso automático ou `None`). Documento e aviso nascem na mesma
    transação, ou nenhum dos dois; quem chama agenda as notificações depois do commit."""
    arquivo = _arquivo(db, logado, dados.arquivo_id)
    aviso_id = None
    if dados.avisar_unidades:
        aviso_id = avisos.gravar_publicacao(db, logado, _aviso_automatico(dados.titulo))
    documento = Documento(
        titulo=dados.titulo,
        categoria=dados.categoria.value,
        data_documento=dados.data_documento,
        acesso=dados.acesso.value,
        criado_por=logado.unidade_id,
        aviso_id=aviso_id,
    )
    db.add(documento)
    _gravar(db)
    db.add(
        DocumentoVersao(
            documento_id=documento.id,
            versao=1,
            arquivo_id=arquivo.id,
            enviada_por=logado.unidade_id,
        )
    )
    _gravar(db)
    registrar(
        db,
        Acao.documento_publicado,
        unidade_id=logado.unidade_id,
        entidade="documento",
        entidade_id=documento.id,
        detalhes={
            "versao": 1,
            "acesso": dados.acesso.value,
            "categoria": dados.categoria.value,
            "avisou": aviso_id is not None,
        },
    )
    try:
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        traduzido = _traduzir(erro)
        if traduzido is None:
            raise
        raise traduzido from erro
    return documento.id, aviso_id


def nova_versao(db: Session, logado: Logado, documento_id: int, dados: NovaVersaoDocumento) -> None:
    """H-19. A trava do documento põe em fila duas versões ao mesmo tempo e o arquivar."""
    documento = _buscar(db, logado, documento_id, travar=True)
    if documento.arquivado_em is not None:
        raise _arquivado()
    arquivo = _arquivo(db, logado, dados.arquivo_id)
    versao = (
        db.scalar(
            select(func.max(DocumentoVersao.versao)).where(
                DocumentoVersao.documento_id == documento.id
            )
        )
        or 0
    ) + 1
    db.add(
        DocumentoVersao(
            documento_id=documento.id,
            versao=versao,
            arquivo_id=arquivo.id,
            enviada_por=logado.unidade_id,
        )
    )
    _gravar(db)
    registrar(
        db,
        Acao.documento_versao_enviada,
        unidade_id=logado.unidade_id,
        entidade="documento",
        entidade_id=documento.id,
        detalhes={"versao": versao},
    )
    db.commit()


def arquivar(db: Session, logado: Logado, documento_id: int) -> None:
    """Sai da lista (continua em "Documentos arquivados", só para a gestão). Arquivar de novo
    não muda nada."""
    documento = _buscar(db, logado, documento_id, travar=True)
    if documento.arquivado_em is not None:
        return
    documento.arquivado_em = func.now()
    registrar(
        db,
        Acao.documento_arquivado,
        unidade_id=logado.unidade_id,
        entidade="documento",
        entidade_id=documento.id,
    )
    db.commit()
