"""Onde moram os arquivos: o bucket de arquivos do R2 (spec do M3, seção 3; ADR-0004, ADR-0011).

Arquivo comum: os épicos usam, não editam.

O conteúdo nunca passa pela API (a Vercel recusa corpo acima de 4,5 MB): a API dá ao navegador
uma URL assinada, curta, e confere depois. Duas pastas no bucket:

- `envios/<chave>`: onde o navegador põe o arquivo (PUT, 10 minutos, com o tipo e o tamanho
  assinados). Pode ser apagado; o R2 apaga sozinho o que ficar mais de 1 dia (regra de ciclo
  de vida), então apagar aqui é só faxina: se falhar, nada quebra.
- `arquivos/<chave>`: o que foi conferido e publicado. **Nunca apagado nem sobrescrito**: o R2
  tem uma trava nesta pasta, e esta camada nem tem como pedir isso (só recebe a chave, e o único
  "apagar" é o do envio).

`ArmazenamentoS3` fala com o R2 (API do S3, `boto3`, como o `scripts/backup/s3.py`);
`ArmazenamentoFalso` guarda em memória, para os testes. A rota recebe um ou outro por
`obter_armazenamento` (dependência FastAPI): `None` quando os arquivos estão desligados.
"""

import hashlib
import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Annotated, Protocol
from urllib.parse import quote

from fastapi import Depends

from app.configuracao import ConfigArquivos, config_arquivos

VALIDADE_ENVIO = timedelta(minutes=10)
VALIDADE_LEITURA = timedelta(minutes=5)
PASTA_ENVIOS = "envios/"
PASTA_ARQUIVOS = "arquivos/"
CACHE_DA_LEITURA = "private, max-age=300"
# Extensões de cada tipo aceito; a primeira é a que se acrescenta quando falta.
EXTENSOES = {
    "application/pdf": (".pdf",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/webp": (".webp",),
}
_CHAVE = re.compile(r"[0-9a-f]{32}")
_FORA_DO_ASCII_SEGURO = re.compile(r"[^A-Za-z0-9 ._()-]")


class ObjetoAusente(Exception):
    """O envio não está no bucket (o navegador não mandou, ou já foi apagado)."""


class FalhaNoArmazenamento(Exception):
    """O bucket não respondeu como devia (fora do ar, chave sem permissão, bucket errado)."""


class EnvioMudou(Exception):
    """O envio não é mais o que foi conferido (ETag diferente): outro PUT na mesma URL trocou o
    conteúdo entre o HEAD e a leitura, ou entre a leitura e a publicação."""


class EnvioRecusado(Exception):
    """O bucket recusou o PUT: fora do que a URL assinada permite (ex.: outro tamanho)."""


class ObjetoTravado(Exception):
    """Já existe um arquivo publicado com esta chave: o bucket não deixa sobrescrever."""


@dataclass(frozen=True)
class UrlAssinada:
    url: str
    expira_em: datetime


@dataclass(frozen=True)
class EnvioRecebido:
    """O que o HEAD do envio diz: o tamanho real e o ETag, a identidade **deste** conteúdo. A
    leitura do começo e a publicação exigem o mesmo ETag, então o que é publicado é exatamente
    o que foi conferido."""

    tamanho: int
    etag: str


class Armazenamento(Protocol):
    def url_de_envio(self, chave: str, tipo: str, tamanho: int) -> UrlAssinada: ...

    def url_de_leitura(self, chave: str, *, tipo: str, nome: str, baixar: bool) -> UrlAssinada: ...

    def envio_recebido(self, chave: str) -> EnvioRecebido | None: ...

    def inicio_do_envio(self, chave: str, n: int = 16, *, etag: str) -> bytes: ...

    def publicar(self, chave: str, tipo: str, *, etag: str) -> None: ...

    # Quem chama apaga o envio depois de publicar (e não falha se não conseguir).
    def descartar_envio(self, chave: str) -> None: ...


def _conferir(chave: str) -> str:
    """A chave vira caminho no bucket: só os 32 hexadecimais que a API gera."""
    if not _CHAVE.fullmatch(chave):
        raise ValueError("chave de arquivo fora do formato")
    return chave


def nome_para_baixar(nome: str, tipo: str) -> str:
    """O nome com a extensão do tipo conferido (um PNG chamado `foto.jpg` baixa `foto.png`)."""
    certas = EXTENSOES[tipo]
    minusculo = nome.lower()
    if minusculo.endswith(certas):
        return nome
    for outras in EXTENSOES.values():
        for extensao in outras:
            if minusculo.endswith(extensao):
                return nome[: -len(extensao)] + certas[0]
    return nome + certas[0]


def disposicao(nome: str, tipo: str, *, baixar: bool) -> str:
    """`Content-Disposition` da leitura: `inline` (abre no celular) ou `attachment` (baixa), com o
    nome em UTF-8 (RFC 6266) e um nome ASCII de reserva para navegador antigo."""
    completo = nome_para_baixar(nome, tipo)
    reserva = unicodedata.normalize("NFKD", completo).encode("ascii", "ignore").decode()
    reserva = _FORA_DO_ASCII_SEGURO.sub("_", reserva).strip()
    extensao = EXTENSOES[tipo][0]
    if not reserva or reserva.lower() in {e for e in EXTENSOES[tipo]}:
        reserva = "arquivo" + extensao
    modo = "attachment" if baixar else "inline"
    return f"{modo}; filename=\"{reserva}\"; filename*=UTF-8''{quote(completo, safe='')}"


def _agora() -> datetime:
    return datetime.now(UTC)


_NAO_EXISTE = {"404", "NoSuchKey", "NotFound"}
_CONDICAO_FALHOU = {"412", "PreconditionFailed"}


def _codigo(erro: Exception) -> str | None:
    """O código de erro de um `ClientError` do boto3."""
    return getattr(erro, "response", {}).get("Error", {}).get("Code")


def _etag_de(conteudo: bytes) -> str:
    """O ETag de um objeto enviado de uma vez só: o MD5 do conteúdo, entre aspas (S3 e R2)."""
    return f'"{hashlib.md5(conteudo).hexdigest()}"'  # noqa: S324 - identidade, não segurança


class ArmazenamentoS3:
    """O bucket de arquivos do R2, pela API do S3."""

    def __init__(self, config: ConfigArquivos) -> None:
        # Import aqui: o boto3 pesa na partida da função, e só as rotas de arquivo precisam.
        import boto3
        from botocore.config import Config

        self._bucket = config.bucket
        self.cliente = boto3.client(
            "s3",
            endpoint_url=config.endpoint,
            aws_access_key_id=config.chave_id,
            aws_secret_access_key=config.chave_secreta,
            region_name=config.regiao,
            config=Config(
                signature_version="s3v4",
                # Caminho no endereço (`<conta>.r2.cloudflarestorage.com/<bucket>/...`): o
                # mesmo host para todo arquivo, que é o que a CSP libera.
                s3={"addressing_style": "path"},
                # O R2 não aceita todos os checksums novos do boto3; só quando a operação exige.
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=15,
            ),
        )

    def url_de_envio(self, chave: str, tipo: str, tamanho: int) -> UrlAssinada:
        # O Content-Type e o Content-Length entram na assinatura: o navegador tem de mandar
        # exatamente este tipo e exatamente o tamanho declarado no pedido. Sem o tamanho, a
        # mesma URL aceitaria gigabytes declarando 209 bytes (o R2 cobra e enche o bucket).
        url = self.cliente.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": PASTA_ENVIOS + _conferir(chave),
                "ContentType": tipo,
                "ContentLength": tamanho,
            },
            ExpiresIn=int(VALIDADE_ENVIO.total_seconds()),
            HttpMethod="PUT",
        )
        return UrlAssinada(url=url, expira_em=_agora() + VALIDADE_ENVIO)

    def url_de_leitura(self, chave: str, *, tipo: str, nome: str, baixar: bool) -> UrlAssinada:
        url = self.cliente.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": PASTA_ARQUIVOS + _conferir(chave),
                # O tipo conferido, não o que o navegador mandou no envio.
                "ResponseContentType": tipo,
                "ResponseContentDisposition": disposicao(nome, tipo, baixar=baixar),
                "ResponseCacheControl": CACHE_DA_LEITURA,
            },
            ExpiresIn=int(VALIDADE_LEITURA.total_seconds()),
        )
        return UrlAssinada(url=url, expira_em=_agora() + VALIDADE_LEITURA)

    @contextmanager
    def _falando_com_o_bucket(self, caminho: str) -> Iterator[None]:
        """Traduz os erros do boto3: "não existe" (`ObjetoAusente`), "ETag mudou"
        (`EnvioMudou`) e qualquer outro (`FalhaNoArmazenamento`, que a rota responde como 503,
        nunca como erro interno cru)."""
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            yield
        except ClientError as erro:
            codigo = _codigo(erro)
            if codigo in _NAO_EXISTE:
                raise ObjetoAusente(caminho) from erro
            if codigo in _CONDICAO_FALHOU:
                raise EnvioMudou(caminho) from erro
            raise FalhaNoArmazenamento(f"{codigo} em {caminho}") from erro
        except BotoCoreError as erro:
            raise FalhaNoArmazenamento(f"{type(erro).__name__} em {caminho}") from erro

    def _cabecalho(self, caminho: str) -> dict | None:
        try:
            with self._falando_com_o_bucket(caminho):
                return self.cliente.head_object(Bucket=self._bucket, Key=caminho)
        except ObjetoAusente:
            return None

    def envio_recebido(self, chave: str) -> EnvioRecebido | None:
        resposta = self._cabecalho(PASTA_ENVIOS + _conferir(chave))
        if resposta is None:
            return None
        return EnvioRecebido(tamanho=int(resposta["ContentLength"]), etag=resposta["ETag"])

    def inicio_do_envio(self, chave: str, n: int = 16, *, etag: str) -> bytes:
        caminho = PASTA_ENVIOS + _conferir(chave)
        with self._falando_com_o_bucket(caminho):
            resposta = self.cliente.get_object(
                Bucket=self._bucket, Key=caminho, Range=f"bytes=0-{n - 1}", IfMatch=etag
            )
            return resposta["Body"].read(n)

    def publicar(self, chave: str, tipo: str, *, etag: str) -> None:
        destino = PASTA_ARQUIVOS + _conferir(chave)
        # Idempotente: uma tentativa anterior pode ter copiado e falhado depois (a linha ficou
        # pendente). Copiar por cima de arquivos/ travado falharia sempre no R2.
        publicado = self._cabecalho(destino)
        if publicado is not None:
            if publicado["ETag"] == etag:
                return
            raise ObjetoTravado(destino)
        with self._falando_com_o_bucket(PASTA_ENVIOS + chave):
            # Só copia se o envio ainda é o conferido (o R2 respeita o CopySourceIfMatch).
            self.cliente.copy_object(
                Bucket=self._bucket,
                Key=destino,
                CopySource={"Bucket": self._bucket, "Key": PASTA_ENVIOS + chave},
                CopySourceIfMatch=etag,
                ContentType=tipo,
                MetadataDirective="REPLACE",
            )

    def descartar_envio(self, chave: str) -> None:
        caminho = PASTA_ENVIOS + _conferir(chave)
        # Apagar o que não existe não é erro no S3.
        with self._falando_com_o_bucket(caminho):
            self.cliente.delete_object(Bucket=self._bucket, Key=caminho)


class ArmazenamentoFalso:
    """Bucket em memória, para os testes. `receber` faz o papel do navegador (o PUT na URL
    assinada: recusa outro tamanho, como o R2); `gravar_por_fora` escreve sem passar pela
    assinatura (alguém com a chave, ou um bug), para testar as defesas da confirmação. Publicar
    por cima de um arquivo já publicado falha, como a trava do R2."""

    BASE = "https://armazenamento.falso"

    def __init__(self) -> None:
        # caminho → (conteúdo, tipo)
        self.objetos: dict[str, tuple[bytes, str]] = {}
        # chave → tamanho assinado na URL de envio
        self.tamanho_assinado: dict[str, int] = {}

    def receber(self, chave: str, conteudo: bytes, tipo: str = "application/pdf") -> None:
        assinado = self.tamanho_assinado.get(_conferir(chave))
        if assinado is not None and assinado != len(conteudo):
            raise EnvioRecusado(f"Content-Length {len(conteudo)} != {assinado}")
        self.gravar_por_fora(chave, conteudo, tipo)

    def gravar_por_fora(self, chave: str, conteudo: bytes, tipo: str = "application/pdf") -> None:
        self.objetos[PASTA_ENVIOS + _conferir(chave)] = (conteudo, tipo)

    def url_de_envio(self, chave: str, tipo: str, tamanho: int) -> UrlAssinada:
        self.tamanho_assinado[_conferir(chave)] = tamanho
        url = f"{self.BASE}/{PASTA_ENVIOS}{_conferir(chave)}?tipo={quote(tipo, safe='')}"
        return UrlAssinada(url=url, expira_em=_agora() + VALIDADE_ENVIO)

    def url_de_leitura(self, chave: str, *, tipo: str, nome: str, baixar: bool) -> UrlAssinada:
        consulta = f"tipo={quote(tipo, safe='')}&baixar={int(baixar)}"
        url = f"{self.BASE}/{PASTA_ARQUIVOS}{_conferir(chave)}?{consulta}"
        return UrlAssinada(url=url, expira_em=_agora() + VALIDADE_LEITURA)

    def envio_recebido(self, chave: str) -> EnvioRecebido | None:
        objeto = self.objetos.get(PASTA_ENVIOS + _conferir(chave))
        if objeto is None:
            return None
        return EnvioRecebido(tamanho=len(objeto[0]), etag=_etag_de(objeto[0]))

    def _envio(self, chave: str, etag: str) -> bytes:
        caminho = PASTA_ENVIOS + _conferir(chave)
        if caminho not in self.objetos:
            raise ObjetoAusente(caminho)
        conteudo = self.objetos[caminho][0]
        if _etag_de(conteudo) != etag:
            raise EnvioMudou(caminho)
        return conteudo

    def inicio_do_envio(self, chave: str, n: int = 16, *, etag: str) -> bytes:
        return self._envio(chave, etag)[:n]

    def publicar(self, chave: str, tipo: str, *, etag: str) -> None:
        destino = PASTA_ARQUIVOS + _conferir(chave)
        if destino in self.objetos:
            if _etag_de(self.objetos[destino][0]) == etag:
                return
            raise ObjetoTravado(destino)
        self.objetos[destino] = (self._envio(chave, etag), tipo)

    def descartar_envio(self, chave: str) -> None:
        self.objetos.pop(PASTA_ENVIOS + _conferir(chave), None)


@cache
def _s3_para(config: ConfigArquivos) -> ArmazenamentoS3:
    return ArmazenamentoS3(config)


def obter_armazenamento() -> Armazenamento | None:
    """Dependência FastAPI: o R2 configurado, ou `None` (arquivos desligados: a rota responde
    503 `arquivos_desligados`). Os testes trocam pelo `ArmazenamentoFalso`."""
    config = config_arquivos()
    return None if config is None else _s3_para(config)


# Parâmetro de rota: `bucket: Armazenado` (None = arquivos desligados; `arquivos.exigir` dá 503).
Armazenado = Annotated[Armazenamento | None, Depends(obter_armazenamento)]
