"""Classificados entre vizinhos: ler, anunciar, editar, reservar, renovar, encerrar, avisar a
gestão e apagar o que é da unidade (spec de 20/10/2026, seções 3, 4 e 7). A moderação e a faxina
ficam em `classificados_gestao.py`; as fotos, em `classificados_fotos.py`.

As rotas só traduzem HTTP. O banco garante o resto (migração 0011): unidade ativa, situação,
vencimento, janela de renovar, escondido travado, limites, até 4 fotos. Quando ele recusa,
`classificados_banco.traduzir` dá o 4xx.

A busca é em Python (`normalizar`, o mesmo das indicações): são no máximo alguns milhares de
anúncios abertos, sem paginação, então nada é agregado depois de paginar.
"""

from dataclasses import dataclass

from sqlalchemy import Row, delete, func, literal_column, select, text, true
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.classificados import (
    Anuncio,
    AnuncioResumo,
    CategoriaClassificado,
    FotoDoAnuncio,
    ListaClassificados,
    NovoAnuncio,
)
from app.esquemas.comum import UnidadeRef
from app.esquemas.indicacoes import AvisarGestao, AvisoRecebido
from app.modelos import Unidade
from app.modelos.classificados import (
    DIAS_PARA_RENOVAR,
    AnuncioFoto,
    AvisoAnuncio,
    MotivoEncerramento,
    SituacaoAnuncio,
    TipoAnuncio,
)
from app.modelos.classificados import Anuncio as AnuncioModelo
from app.modelos.classificados import CategoriaClassificado as CategoriaModelo
from app.seguranca.dependencias import Logado
from app.servicos import classificados_banco, classificados_fotos
from app.servicos.armazenamento import Armazenamento
from app.servicos.indicacoes import normalizar

_JANELA_DE_RENOVAR = literal_column(f"interval '{DIAS_PARA_RENOVAR} days'")

# --- erros -------------------------------------------------------------------------------------


def indisponivel() -> ErroApi:
    return ErroApi(*classificados_banco.INDISPONIVEL)


def _so_o_dono() -> ErroApi:
    return ErroApi(403, "sem_permissao", "Só o apartamento que anunciou pode mudar este anúncio.")


def _repassar(db: Session, erro: DBAPIError) -> ErroApi:
    """Desfaz a transação e devolve o 4xx do banco (ou levanta o erro, que vira 500)."""
    db.rollback()
    traduzido = classificados_banco.traduzir(erro)
    if traduzido is None:
        raise erro
    return traduzido


def _gravar(db: Session) -> None:
    try:
        db.commit()
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro


# --- leitura -----------------------------------------------------------------------------------


def listar_categorias(db: Session) -> list[CategoriaClassificado]:
    return [
        CategoriaClassificado(id=c.id, nome=c.nome)
        for c in db.scalars(
            select(CategoriaModelo).order_by(CategoriaModelo.ordem, CategoriaModelo.id)
        )
    ]


# Os cartões numa consulta: a categoria, a placa, a capa (a foto de ordem 0, por `lateral`), os
# avisos abertos e o vencido calculado pelo relógio do banco. Quem filtra é o `where` de cada uso.
_CARTOES = """
select a.id, a.tipo, a.titulo, a.descricao, a.preco_centavos, a.situacao,
       coalesce(a.renovado_em, a.publicado_em) as em, a.vence_em <= now() as vencido,
       a.escondido_em is not null as escondido, a.unidade_id,
       c.id as categoria_id, c.nome as categoria_nome, u.login,
       f.chave as capa_chave, f.tipo as capa_tipo,
       (select count(*) from aviso_anuncio v
         where v.anuncio_id = a.id and v.resolvido_em is null) as avisos
  from anuncio a
  join categoria_classificado c on c.id = a.categoria_id
  join unidade u on u.id = a.unidade_id
  left join lateral (
      select x.chave, x.tipo from anuncio_foto x
       where x.anuncio_id = a.id order by x.ordem limit 1
  ) f on true
"""


def _capa(armazenamento: Armazenamento | None, linha: Row) -> str | None:
    if armazenamento is None or linha.capa_chave is None:
        return None
    return armazenamento.url_da_foto(linha.capa_chave, tipo=linha.capa_tipo).url


def _resumo(linha: Row, logado: Logado, armazenamento: Armazenamento | None) -> AnuncioResumo:
    return AnuncioResumo(
        id=linha.id,
        tipo=TipoAnuncio(linha.tipo),
        categoria=CategoriaClassificado(id=linha.categoria_id, nome=linha.categoria_nome),
        titulo=linha.titulo,
        preco_centavos=linha.preco_centavos,
        capa=_capa(armazenamento, linha),
        unidade=UnidadeRef.de_login(linha.login),
        em=linha.em,
        situacao=SituacaoAnuncio(linha.situacao),
        vencido=linha.vencido,
        escondido=linha.escondido,
        avisos_abertos=linha.avisos if logado.gestao else None,
    )


def _bate(linha: Row, termo: str) -> bool:
    return termo in normalizar(f"{linha.titulo} {linha.descricao or ''} {linha.categoria_nome}")


def listar(
    db: Session,
    logado: Logado,
    armazenamento: Armazenamento | None,
    *,
    tipo: TipoAnuncio | None,
    categoria: int | None,
    busca: str | None,
    com_aviso: bool,
) -> ListaClassificados:
    """Ativos e reservados, não vencidos nem escondidos, o mais recente primeiro (publicação ou
    renovação). `com_aviso` (só a gestão): os que têm aviso aberto, não escondidos nem
    encerrados (vencidos inclusive)."""
    com_aviso = com_aviso and logado.gestao
    termo = normalizar(busca or "")
    linhas = db.execute(
        text(
            _CARTOES + " where a.escondido_em is null and a.situacao <> 'encerrado'"
            " order by coalesce(a.renovado_em, a.publicado_em) desc, a.id desc"
        )
    ).all()
    contagem = sum(1 for linha in linhas if linha.avisos > 0)
    itens = []
    for linha in linhas:
        if com_aviso:
            if linha.avisos == 0:
                continue
        elif linha.vencido:
            continue
        if tipo is not None and linha.tipo != tipo:
            continue
        if categoria is not None and linha.categoria_id != categoria:
            continue
        if termo and not _bate(linha, termo):
            continue
        itens.append(_resumo(linha, logado, armazenamento))
    meus = db.scalar(
        select(func.count())
        .select_from(AnuncioModelo)
        .where(AnuncioModelo.unidade_id == logado.unidade_id)
    )
    return ListaClassificados(
        itens=itens, com_aviso=contagem if logado.gestao else None, meus=int(meus or 0)
    )


def meus(db: Session, logado: Logado, armazenamento: Armazenamento | None) -> list[AnuncioResumo]:
    """Todos os da unidade, enquanto existirem: os abertos primeiro, depois os vencidos, depois
    os encerrados; em cada grupo, o mais recente primeiro."""
    linhas = db.execute(
        text(
            _CARTOES + " where a.unidade_id = :u"
            " order by case when a.situacao = 'encerrado' then 2"
            " when a.vence_em <= now() then 1 else 0 end,"
            " coalesce(a.encerrado_em, a.renovado_em, a.publicado_em) desc, a.id desc"
        ),
        {"u": logado.unidade_id},
    ).all()
    return [_resumo(linha, logado, armazenamento) for linha in linhas]


@dataclass(frozen=True)
class _Encontrado:
    anuncio: AnuncioModelo
    vencido: bool
    meu: bool

    @property
    def visivel(self) -> bool:
        a = self.anuncio
        return (
            a.escondido_em is None and a.situacao != SituacaoAnuncio.encerrado and not self.vencido
        )


def _buscar(db: Session, logado: Logado, anuncio_id: int, *, travar: bool = False) -> _Encontrado:
    """O anúncio, ou 404 com a frase "Este anúncio não está mais disponível." para quem não é o
    dono nem a gestão quando ele venceu, foi encerrado ou escondido."""
    consulta = select(AnuncioModelo, (AnuncioModelo.vence_em <= func.now()).label("vencido")).where(
        AnuncioModelo.id == anuncio_id
    )
    if travar:
        consulta = consulta.with_for_update(of=AnuncioModelo)
    linha = db.execute(consulta).one_or_none()
    if linha is None:
        raise indisponivel()
    achado = _Encontrado(
        anuncio=linha[0], vencido=bool(linha[1]), meu=linha[0].unidade_id == logado.unidade_id
    )
    if not (achado.visivel or achado.meu or logado.gestao):
        raise indisponivel()
    return achado


def _do_dono(db: Session, logado: Logado, anuncio_id: int) -> _Encontrado:
    """O anúncio travado até o fim da transação, se a unidade logada é a dona; senão 403 (a
    gestão só esconde) ou 404."""
    achado = _buscar(db, logado, anuncio_id, travar=True)
    if not achado.meu:
        db.rollback()
        raise _so_o_dono()
    return achado


def _fotos(
    db: Session, armazenamento: Armazenamento | None, anuncio_id: int
) -> list[FotoDoAnuncio]:
    if armazenamento is None:
        return []
    return [
        FotoDoAnuncio(id=f.id, url=armazenamento.url_da_foto(f.chave, tipo=f.tipo).url)
        for f in db.scalars(
            select(AnuncioFoto)
            .where(AnuncioFoto.anuncio_id == anuncio_id)
            .order_by(AnuncioFoto.ordem)
        )
    ]


def abrir(
    db: Session, logado: Logado, armazenamento: Armazenamento | None, anuncio_id: int
) -> Anuncio:
    achado = _buscar(db, logado, anuncio_id)
    a = achado.anuncio
    categoria = db.get_one(CategoriaModelo, a.categoria_id)
    login = db.scalar(select(Unidade.login).where(Unidade.id == a.unidade_id))
    perto = db.scalar(
        select(AnuncioModelo.vence_em <= func.now() + _JANELA_DE_RENOVAR).where(
            AnuncioModelo.id == a.id
        )
    )
    ja_avisei = (
        db.scalar(
            select(AvisoAnuncio.id).where(
                AvisoAnuncio.anuncio_id == a.id,
                AvisoAnuncio.unidade_id == logado.unidade_id,
                AvisoAnuncio.resolvido_em.is_(None),
            )
        )
        is not None
    )
    avisos = None
    if logado.gestao:
        avisos = [
            AvisoRecebido(id=v.id, motivo=v.motivo, em=v.criado_em)
            for v in db.scalars(
                select(AvisoAnuncio)
                .where(AvisoAnuncio.anuncio_id == a.id, AvisoAnuncio.resolvido_em.is_(None))
                .order_by(AvisoAnuncio.criado_em.desc(), AvisoAnuncio.id.desc())
            )
        ]
    aberto = a.situacao != SituacaoAnuncio.encerrado and a.escondido_em is None
    return Anuncio(
        id=a.id,
        tipo=TipoAnuncio(a.tipo),
        categoria=CategoriaClassificado(id=categoria.id, nome=categoria.nome),
        titulo=a.titulo,
        descricao=a.descricao,
        preco_centavos=a.preco_centavos,
        contato=a.contato,
        celular=len(a.contato) == 11,
        unidade=UnidadeRef.de_login(login),
        publicado_em=a.publicado_em,
        renovado_em=a.renovado_em,
        vence_em=a.vence_em,
        situacao=SituacaoAnuncio(a.situacao),
        motivo_encerramento=(
            None if a.motivo_encerramento is None else MotivoEncerramento(a.motivo_encerramento)
        ),
        vencido=achado.vencido,
        escondido=a.escondido_em is not None,
        fotos=_fotos(db, armazenamento, a.id),
        meu=achado.meu,
        pode_renovar=achado.meu and aberto and bool(perto),
        ja_avisei=ja_avisei,
        avisos=avisos,
    )


# --- anunciar e editar -------------------------------------------------------------------------


def _foto_invalida() -> ErroApi:
    return ErroApi(*classificados_banco.FOTO)


def _prender_fotos(db: Session, logado: Logado, anuncio_id: int, fotos: list[int]) -> None:
    """Põe as fotos no anúncio, na ordem. As que já estão nele só mudam de ordem; as novas têm de
    ser desta unidade, confirmadas e soltas."""
    for ordem, foto_id in enumerate(fotos):
        foto = db.scalars(
            select(AnuncioFoto)
            .where(AnuncioFoto.id == foto_id, AnuncioFoto.unidade_id == logado.unidade_id)
            .with_for_update()
        ).one_or_none()
        if foto is None or foto.descartada_em is not None or foto.confirmada_em is None:
            raise _foto_invalida()
        if foto.anuncio_id is not None and foto.anuncio_id != anuncio_id:
            raise _foto_invalida()
        foto.anuncio_id = anuncio_id
        foto.ordem = ordem
        db.flush()


def criar(db: Session, logado: Logado, dados: NovoAnuncio) -> int:
    try:
        anuncio = AnuncioModelo(
            unidade_id=logado.unidade_id,
            categoria_id=dados.categoria_id,
            tipo=dados.tipo.value,
            titulo=dados.titulo,
            descricao=dados.descricao,
            preco_centavos=dados.preco_centavos,
            contato=dados.contato,
        )
        db.add(anuncio)
        db.flush()
        anuncio_id = anuncio.id
        _prender_fotos(db, logado, anuncio_id, dados.fotos)
        db.commit()
    except ErroApi:
        db.rollback()
        raise
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    return anuncio_id


def _conferir_aberto(achado: _Encontrado) -> None:
    """Escondido, encerrado ou vencido: só encerrar (o vencido também renova)."""
    a = achado.anuncio
    if a.escondido_em is not None:
        raise ErroApi(*classificados_banco.ESCONDIDO)
    if a.situacao == SituacaoAnuncio.encerrado:
        raise ErroApi(*classificados_banco.ENCERRADO)
    if achado.vencido:
        raise ErroApi(*classificados_banco.VENCIDO)


def editar(
    db: Session,
    logado: Logado,
    armazenamento: Armazenamento | None,
    anuncio_id: int,
    dados: NovoAnuncio,
) -> None:
    """Tudo de novo, com as fotos na ordem nova. A foto que saiu é descartada e apagada do bucket
    logo depois do commit."""
    achado = _do_dono(db, logado, anuncio_id)
    try:
        _conferir_aberto(achado)
        a = achado.anuncio
        a.categoria_id = dados.categoria_id
        a.tipo = dados.tipo.value
        a.titulo = dados.titulo
        a.descricao = dados.descricao
        a.preco_centavos = dados.preco_centavos
        a.contato = dados.contato
        db.flush()
        tiradas = classificados_fotos.descartar(
            db,
            AnuncioFoto.anuncio_id == anuncio_id,
            AnuncioFoto.id.not_in(dados.fotos) if dados.fotos else true(),
        )
        _prender_fotos(db, logado, anuncio_id, dados.fotos)
        db.commit()
    except ErroApi:
        db.rollback()
        raise
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    classificados_fotos.varrer(db, armazenamento, tiradas)


def _mudar(db: Session, logado: Logado, anuncio_id: int, **valores) -> None:
    achado = _do_dono(db, logado, anuncio_id)
    try:
        for campo, valor in valores.items():
            setattr(achado.anuncio, campo, valor)
        db.flush()
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    _gravar(db)


def reservar(db: Session, logado: Logado, anuncio_id: int) -> None:
    _mudar(db, logado, anuncio_id, situacao=SituacaoAnuncio.reservado.value)


def liberar(db: Session, logado: Logado, anuncio_id: int) -> None:
    _mudar(db, logado, anuncio_id, situacao=SituacaoAnuncio.ativo.value)


def renovar(db: Session, logado: Logado, anuncio_id: int) -> None:
    """O banco carimba `renovado_em` e calcula o vencimento novo (mais 30 dias)."""
    _mudar(db, logado, anuncio_id, renovado_em=func.now())


def encerrar(db: Session, logado: Logado, anuncio_id: int, motivo: MotivoEncerramento) -> None:
    """Encerrado não volta. As fotos ficam 7 dias (o dono ainda vê em "Meus anúncios"); a
    faxina apaga depois."""
    _mudar(
        db,
        logado,
        anuncio_id,
        situacao=SituacaoAnuncio.encerrado.value,
        motivo_encerramento=motivo.value,
    )


# --- avisar ------------------------------------------------------------------------------------


def avisar(db: Session, logado: Logado, anuncio_id: int, dados: AvisarGestao) -> int | None:
    """ "Tem algo errado aqui?". Repetir é idempotente. Devolve o id do aviso quando ele é o
    **primeiro aberto** do anúncio (a rota manda o e-mail à administração), ou `None`."""
    achado = _buscar(db, logado, anuncio_id, travar=True)
    if not achado.visivel:
        db.rollback()
        raise indisponivel()
    abertos = list(
        db.scalars(
            select(AvisoAnuncio.unidade_id).where(
                AvisoAnuncio.anuncio_id == anuncio_id, AvisoAnuncio.resolvido_em.is_(None)
            )
        )
    )
    if logado.unidade_id in abertos:
        db.rollback()
        return None
    aviso = AvisoAnuncio(anuncio_id=anuncio_id, unidade_id=logado.unidade_id, motivo=dados.motivo)
    try:
        db.add(aviso)
        db.flush()
        aviso_id = aviso.id
        db.commit()
    except DBAPIError as falha:
        if classificados_banco.restricao(falha) == "aviso_anuncio_aberto":
            db.rollback()
            return None
        raise _repassar(db, falha) from falha
    return aviso_id if not abertos else None


# --- "apagar meus dados" e reset ---------------------------------------------------------------


def apagar_da_unidade(db: Session, unidade_id: int) -> list[int]:
    """Apaga os anúncios da unidade (com os avisos que receberam) e os avisos que ela mandou, e
    descarta todas as fotos dela. Devolve as ids das fotos, para quem chama varrer o bucket
    depois do commit (`classificados_fotos.varrer(..., apagar_linhas=True)`). Sem commit."""
    fotos = classificados_fotos.descartar(db, AnuncioFoto.unidade_id == unidade_id)
    db.execute(delete(AvisoAnuncio).where(AvisoAnuncio.unidade_id == unidade_id))
    db.execute(delete(AnuncioModelo).where(AnuncioModelo.unidade_id == unidade_id))
    return fotos
