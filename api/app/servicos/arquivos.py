"""Envio de arquivo (spec do M3, seção 4). Arquivo comum: os épicos usam, não editam.

1. `pedir_envio`: confere papel, tipo e tamanho declarados, grava o `arquivo` pendente com uma
   chave aleatória e devolve a URL de envio (PUT em `envios/<chave>`, 10 minutos).
2. O navegador manda o arquivo direto ao bucket.
3. `confirmar_envio`: lê o tamanho **real** e os primeiros bytes. Fora do limite, ou sem a
   assinatura de PDF, JPEG, PNG ou WEBP (um `.exe` renomeado para `.pdf`): apaga o envio, apaga
   a linha, registra `arquivo_recusado` e responde 422. Senão, publica em `arquivos/<chave>`
   (nunca mais apagado, ADR-0011) e marca o arquivo como confirmado.

Para os épicos: `arquivo_utilizavel` (o arquivo pode entrar num documento ou aviso desta
unidade?), `como_enviado` (o `ArquivoEnviado` de uma linha) e `link_do_arquivo` (o link curto
de leitura, depois de o épico conferir quem pode ver).
"""

import secrets

import psycopg
from sqlalchemy import delete, func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.erros_api import ErroApi
from app.esquemas.arquivos import (
    ArquivoEnviado,
    EnvioAutorizado,
    LinkDoArquivo,
    PedirEnvio,
    mensagem_do_limite,
)
from app.modelos import Arquivo
from app.modelos.arquivos import LIMITE_POR_FINALIDADE
from app.seguranca.dependencias import Logado
from app.servicos.armazenamento import Armazenamento, EnvioMudou, ObjetoAusente
from app.servicos.historico import Acao, registrar

# Quantos bytes do começo bastam para reconhecer os quatro tipos (o WEBP precisa de 12).
BYTES_DA_ASSINATURA = 16
MSG_CONTEUDO = "Este arquivo não é um PDF nem uma foto (JPEG, PNG ou WEBP). Escolha outro."


def tipo_pelo_conteudo(inicio: bytes) -> str | None:
    """O tipo pela assinatura do começo do arquivo (os "bytes mágicos"), nunca pela extensão.
    Qualquer outra coisa (programa, ZIP, HTML, SVG, vazio) é `None`."""
    if inicio.startswith(b"%PDF-"):
        return "application/pdf"
    if inicio.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if inicio.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(inicio) >= 12 and inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP":
        return "image/webp"
    return None


def exigir(armazenamento: Armazenamento | None) -> Armazenamento:
    """O bucket, ou 503 quando os arquivos estão desligados (sem `PORTAL_ARQUIVOS_*`)."""
    if armazenamento is None:
        raise ErroApi(
            503, "arquivos_desligados", "O envio de arquivos ainda não está ligado no Portal."
        )
    return armazenamento


def _nao_encontrado() -> ErroApi:
    return ErroApi(
        404, "arquivo_nao_encontrado", "Não achamos este arquivo. Escolha o arquivo de novo."
    )


def como_enviado(arquivo: Arquivo) -> ArquivoEnviado:
    return ArquivoEnviado(
        id=arquivo.id,
        nome=arquivo.nome_original,
        tipo=arquivo.tipo,
        tamanho_bytes=arquivo.tamanho_bytes,
    )


def pedir_envio(
    db: Session, logado: Logado, dados: PedirEnvio, armazenamento: Armazenamento | None
) -> EnvioAutorizado:
    armazenamento = exigir(armazenamento)
    # Faxina: pendente de mais de 1 dia não vai mais ser confirmado (o objeto dele, se chegou,
    # o R2 apaga sozinho pela regra de ciclo de vida de `envios/`).
    db.execute(
        delete(Arquivo).where(
            Arquivo.confirmado_em.is_(None),
            Arquivo.enviado_em < func.now() - literal_column("interval '1 day'"),
        )
    )
    arquivo = Arquivo(
        chave=secrets.token_hex(16),
        nome_original=dados.nome,
        tipo=dados.tipo.value,
        finalidade=dados.finalidade.value,
        tamanho_bytes=dados.tamanho_bytes,
        enviado_por=logado.unidade_id,
    )
    db.add(arquivo)
    try:
        db.flush()
    except IntegrityError as erro:
        db.rollback()
        if (
            isinstance(erro.orig, psycopg.Error)
            and erro.orig.diag.constraint_name == "arquivo_limite_dia"
        ):
            raise ErroApi(
                409, "muitos_arquivos", "Muitos arquivos enviados hoje. Tente de novo amanhã."
            ) from erro
        raise
    url = armazenamento.url_de_envio(arquivo.chave, arquivo.tipo, arquivo.tamanho_bytes)
    resposta = EnvioAutorizado(
        arquivo_id=arquivo.id, url=url.url, content_type=arquivo.tipo, expira_em=url.expira_em
    )
    db.commit()
    return resposta


def _recusar(
    db: Session,
    logado: Logado,
    arquivo: Arquivo,
    armazenamento: Armazenamento,
    *,
    motivo: str,
    tamanho: int,
    encontrado: str | None,
    mensagem: str,
) -> ErroApi:
    """Apaga o envio e a linha, registra (sem o nome do arquivo) e devolve o 422."""
    armazenamento.descartar_envio(arquivo.chave)
    registrar(
        db,
        Acao.arquivo_recusado,
        unidade_id=logado.unidade_id,
        entidade="arquivo",
        entidade_id=arquivo.id,
        detalhes={
            "motivo": motivo,
            "finalidade": arquivo.finalidade,
            "tipo_declarado": arquivo.tipo,
            "tipo_encontrado": encontrado,
            "tamanho_bytes": tamanho,
        },
    )
    db.delete(arquivo)
    db.commit()
    return ErroApi(422, "arquivo_recusado", mensagem)


def confirmar_envio(
    db: Session, logado: Logado, arquivo_id: int, armazenamento: Armazenamento | None
) -> ArquivoEnviado:
    armazenamento = exigir(armazenamento)
    # Trava a linha: duas confirmações ao mesmo tempo não publicam duas vezes.
    arquivo = db.scalars(
        select(Arquivo)
        .where(Arquivo.id == arquivo_id, Arquivo.enviado_por == logado.unidade_id)
        .with_for_update()
    ).one_or_none()
    if arquivo is None:
        raise _nao_encontrado()
    if arquivo.confirmado_em is not None:
        return como_enviado(arquivo)

    nao_chegou = ErroApi(
        409,
        "arquivo_nao_chegou",
        "O arquivo não chegou ao Portal. Confira a internet e envie de novo.",
    )
    recebido = armazenamento.envio_recebido(arquivo.chave)
    if recebido is None:
        raise nao_chegou
    tamanho = recebido.tamanho
    if tamanho > LIMITE_POR_FINALIDADE[arquivo.finalidade]:
        raise _recusar(
            db,
            logado,
            arquivo,
            armazenamento,
            motivo="tamanho",
            tamanho=tamanho,
            encontrado=None,
            mensagem=mensagem_do_limite(arquivo.finalidade),
        )
    if tamanho == 0:
        raise _recusar(
            db,
            logado,
            arquivo,
            armazenamento,
            motivo="conteudo",
            tamanho=tamanho,
            encontrado=None,
            mensagem=MSG_CONTEUDO,
        )
    # O R2 só aceita pela URL assinada o tamanho declarado; outro tamanho chegou por fora dela.
    # Não é o arquivo que a tela mandou: continua pendente, à espera do envio certo.
    if tamanho != arquivo.tamanho_bytes:
        raise nao_chegou
    try:
        # O começo lido e o objeto publicado são os do ETag do HEAD: um 2º PUT na mesma URL,
        # no meio da conferência, não troca o conteúdo publicado.
        inicio = armazenamento.inicio_do_envio(
            arquivo.chave, BYTES_DA_ASSINATURA, etag=recebido.etag
        )
    except (ObjetoAusente, EnvioMudou) as erro:
        raise nao_chegou from erro
    encontrado = tipo_pelo_conteudo(inicio)
    if encontrado is None:
        raise _recusar(
            db,
            logado,
            arquivo,
            armazenamento,
            motivo="conteudo",
            tamanho=tamanho,
            encontrado=None,
            mensagem=MSG_CONTEUDO,
        )

    # Publica antes de gravar: se o commit falhar, sobra um objeto travado sem linha (pouco e
    # invisível); o contrário deixaria uma linha confirmada apontando para nada.
    try:
        armazenamento.publicar(arquivo.chave, encontrado, etag=recebido.etag)
    except (ObjetoAusente, EnvioMudou) as erro:
        raise nao_chegou from erro
    arquivo.tipo = encontrado
    arquivo.tamanho_bytes = tamanho
    arquivo.confirmado_em = func.now()
    db.commit()
    return como_enviado(arquivo)


def arquivo_utilizavel(
    db: Session, logado: Logado, arquivo_id: int, finalidade: str
) -> Arquivo | None:
    """O arquivo que esta unidade enviou, já confirmado, para esta finalidade; senão `None` (o
    épico responde 422 "Envie o arquivo de novo.")."""
    return db.scalars(
        select(Arquivo).where(
            Arquivo.id == arquivo_id,
            Arquivo.enviado_por == logado.unidade_id,
            Arquivo.finalidade == finalidade,
            Arquivo.confirmado_em.is_not(None),
        )
    ).one_or_none()


def link_do_arquivo(
    armazenamento: Armazenamento | None, arquivo: Arquivo, *, baixar: bool
) -> LinkDoArquivo:
    """O link curto de leitura. **Quem chama já conferiu que a unidade pode ver o arquivo.**"""
    url = exigir(armazenamento).url_de_leitura(
        arquivo.chave, tipo=arquivo.tipo, nome=arquivo.nome_original, baixar=baixar
    )
    return LinkDoArquivo(url=url.url, expira_em=url.expira_em)
