"""As fotos dos classificados (spec de 20/10/2026, seções 3.3 e 6; ADR-0012).

O envio é o do M3 (`app/servicos/arquivos.py`), com a tabela própria `anuncio_foto` e outro
destino:

1. `pedir`: grava a foto pendente com uma chave aleatória e devolve a URL de envio (PUT em
   `envios/<chave>`, 10 minutos, com o tipo e o tamanho assinados).
2. O navegador manda a foto direto ao bucket.
3. `confirmar`: lê o tamanho real e os primeiros bytes. Fora do limite, ou sem a assinatura de
   JPEG, PNG ou WEBP: a foto é **descartada** (conta no limite do dia até a faxina) e a resposta
   é 422. Senão, copia para `classificados/<chave>` (sem trava) e marca como confirmada.

Descartar e varrer: tirar a foto na edição, a faxina, "apagar meus dados" e o reset marcam a
foto como descartada (`descartar_*`, na transação de quem chama); depois do commit, `varrer`
apaga o objeto no bucket e, se a foto foi enviada há mais de 1 dia (ou `apagar_linhas`), a
linha. Se o bucket falhar, a foto fica descartada e a faxina tenta de novo: nada quebra.
"""

import logging
import secrets
from collections.abc import Iterable
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.classificados import (
    MSG_TAMANHO_FOTO,
    FotoAutorizada,
    FotoEnviada,
    PedirFoto,
)
from app.modelos.classificados import LIMITE_FOTO, TIPOS_DE_FOTO, AnuncioFoto
from app.seguranca.dependencias import Logado
from app.servicos import classificados_banco
from app.servicos.armazenamento import (
    Armazenamento,
    EnvioMudou,
    FalhaNoArmazenamento,
    ObjetoAusente,
    ObjetoTravado,
    caminho_da_foto,
)
from app.servicos.arquivos import BYTES_DA_ASSINATURA, exigir, tipo_pelo_conteudo

log = logging.getLogger(__name__)

MSG_NAO_E_FOTO = "Esta foto não é JPEG, PNG nem WEBP. Escolha outra."
# A linha descartada fica 1 dia, para contar no limite do dia (as fotos que entram e saem).
GUARDA_DA_LINHA = timedelta(days=1)


def _repassar(db: Session, erro: DBAPIError) -> ErroApi:
    db.rollback()
    traduzido = classificados_banco.traduzir(erro)
    if traduzido is None:
        raise erro
    return traduzido


def _nao_encontrada() -> ErroApi:
    return ErroApi(404, "foto_nao_encontrada", "Não achamos esta foto. Escolha a foto de novo.")


def _nao_chegou() -> ErroApi:
    return ErroApi(
        409,
        "arquivo_nao_chegou",
        "A foto não chegou ao Portal. Confira a internet e envie de novo.",
    )


def pedir(
    db: Session, logado: Logado, dados: PedirFoto, armazenamento: Armazenamento | None
) -> FotoAutorizada:
    armazenamento = exigir(armazenamento)
    foto = AnuncioFoto(
        unidade_id=logado.unidade_id,
        chave=secrets.token_hex(16),
        tipo=dados.tipo.value,
        bytes=dados.tamanho_bytes,
    )
    try:
        db.add(foto)
        db.flush()
    except DBAPIError as erro:
        raise _repassar(db, erro) from erro
    url = armazenamento.url_de_envio(foto.chave, foto.tipo, foto.bytes)
    resposta = FotoAutorizada(
        foto_id=foto.id, url=url.url, content_type=foto.tipo, expira_em=url.expira_em
    )
    db.commit()
    return resposta


def _descartar_envio_sem_falhar(armazenamento: Armazenamento, chave: str) -> None:
    try:
        armazenamento.descartar_envio(chave)
    except FalhaNoArmazenamento:
        log.warning("envio de foto não apagado (o ciclo de vida do bucket apaga depois)")


def _recusar(
    db: Session, foto: AnuncioFoto, armazenamento: Armazenamento, mensagem: str
) -> ErroApi:
    """Descarta (a linha conta no limite do dia até a faxina) e devolve o 422."""
    _descartar_envio_sem_falhar(armazenamento, foto.chave)
    foto.descartada_em = func.now()
    db.commit()
    return ErroApi(422, "foto_recusada", mensagem)


def confirmar(
    db: Session, logado: Logado, foto_id: int, armazenamento: Armazenamento | None
) -> FotoEnviada:
    armazenamento = exigir(armazenamento)
    try:
        return _confirmar(db, logado, foto_id, armazenamento)
    except FalhaNoArmazenamento as erro:
        log.exception("bucket de arquivos falhou ao confirmar uma foto")
        db.rollback()
        raise ErroApi(
            503,
            "armazenamento_indisponivel",
            "Não deu para guardar a foto agora. Tente de novo em alguns minutos.",
        ) from erro


def _confirmar(
    db: Session, logado: Logado, foto_id: int, armazenamento: Armazenamento
) -> FotoEnviada:
    # Trava a linha: duas confirmações ao mesmo tempo não copiam duas vezes.
    foto = db.scalars(
        select(AnuncioFoto)
        .where(AnuncioFoto.id == foto_id, AnuncioFoto.unidade_id == logado.unidade_id)
        .with_for_update()
    ).one_or_none()
    if foto is None or foto.descartada_em is not None:
        raise _nao_encontrada()
    if foto.confirmada_em is not None:
        return FotoEnviada(id=foto.id)
    recebido = armazenamento.envio_recebido(foto.chave)
    if recebido is None:
        raise _nao_chegou()
    if recebido.tamanho > LIMITE_FOTO:
        raise _recusar(db, foto, armazenamento, MSG_TAMANHO_FOTO)
    if recebido.tamanho == 0:
        raise _recusar(db, foto, armazenamento, MSG_NAO_E_FOTO)
    # Outro tamanho chegou por fora da URL assinada: continua pendente, à espera do envio certo.
    if recebido.tamanho != foto.bytes:
        raise _nao_chegou()
    try:
        inicio = armazenamento.inicio_do_envio(foto.chave, BYTES_DA_ASSINATURA, etag=recebido.etag)
    except (ObjetoAusente, EnvioMudou) as erro:
        raise _nao_chegou() from erro
    encontrado = tipo_pelo_conteudo(inicio)
    if encontrado not in TIPOS_DE_FOTO:
        raise _recusar(db, foto, armazenamento, MSG_NAO_E_FOTO)
    # Copia antes de gravar (como no M3): se o commit falhar, a confirmação seguinte vê a cópia
    # com o mesmo ETag e grava.
    try:
        armazenamento.publicar_foto(foto.chave, encontrado, etag=recebido.etag)
    except (ObjetoAusente, EnvioMudou, ObjetoTravado) as erro:
        raise _nao_chegou() from erro
    foto.tipo = encontrado
    foto.confirmada_em = func.now()
    db.commit()
    _descartar_envio_sem_falhar(armazenamento, foto.chave)
    return FotoEnviada(id=foto_id)


# --- descartar e varrer ------------------------------------------------------------------------


def descartar(db: Session, *condicoes) -> list[int]:
    """Marca como descartadas as fotos (não descartadas) que batem com `condicoes` e devolve as
    ids. Sem commit. O objeto sai no `varrer`, depois do commit."""
    return list(
        db.scalars(
            update(AnuncioFoto)
            .where(AnuncioFoto.descartada_em.is_(None), *condicoes)
            .values(anuncio_id=None, ordem=None, descartada_em=func.now())
            .returning(AnuncioFoto.id)
        )
    )


def varrer(
    db: Session,
    armazenamento: Armazenamento | None,
    ids: Iterable[int] | None = None,
    *,
    apagar_linhas: bool = False,
) -> int:
    """Apaga do bucket as fotos descartadas (as de `ids`, ou todas) e, se a foto foi enviada há
    mais de 1 dia (ou `apagar_linhas`), a linha. Devolve quantas linhas saíram (cada foto conta
    uma vez, quando some de vez). Nunca levanta
    por causa do bucket: o que falhar fica para a faxina."""
    if armazenamento is None:
        return 0
    consulta = select(AnuncioFoto).where(AnuncioFoto.descartada_em.is_not(None))
    if ids is not None:
        lista = list(ids)
        if not lista:
            return 0
        consulta = consulta.where(AnuncioFoto.id.in_(lista))
    limite = db.scalar(select(func.now() - GUARDA_DA_LINHA))
    apagados = 0
    for foto in db.scalars(consulta.order_by(AnuncioFoto.id)).all():
        try:
            # Os dois, sempre (os dois apagares aceitam o que não existe): a cópia para
            # `classificados/` pode ter chegado ao bucket sem a confirmação ter sido gravada
            # (revisão M2), e o envio pode ter sobrado em `envios/`.
            armazenamento.descartar_envio(foto.chave)
            armazenamento.apagar_classificado(caminho_da_foto(foto.chave))
        except FalhaNoArmazenamento:
            log.warning("foto de classificado não apagada agora (a faxina tenta de novo)")
            continue
        if apagar_linhas or foto.enviada_em < limite:
            db.delete(foto)
            apagados += 1
    db.commit()
    return apagados
