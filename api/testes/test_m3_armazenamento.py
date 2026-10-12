"""Camada de armazenamento (spec do M3, seção 3; ADR-0011).

Os mesmos casos rodam contra o `ArmazenamentoS3` (falando com o `moto`, um S3 falso dentro do
processo, no endereço de um R2 fictício) e contra o `ArmazenamentoFalso` dos testes da API.
Nenhum teste fala com o R2 de verdade.
"""

import hashlib
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

ENDPOINT = "https://conta-ficticia.r2.cloudflarestorage.com"
# O moto lê os endereços de S3 próprios quando é importado: antes do import.
os.environ.setdefault("MOTO_S3_CUSTOM_ENDPOINTS", ENDPOINT)

from moto import mock_aws  # noqa: E402

from app import configuracao  # noqa: E402
from app.configuracao import ConfigArquivos  # noqa: E402
from app.servicos import armazenamento  # noqa: E402
from app.servicos.armazenamento import (  # noqa: E402
    ArmazenamentoFalso,
    ArmazenamentoS3,
    EnvioMudou,
    EnvioRecusado,
    FalhaNoArmazenamento,
    ObjetoAusente,
    ObjetoTravado,
    disposicao,
    nome_para_baixar,
)

BUCKET = "portal-capibaribe-arquivos"
CHAVE = "0123456789abcdef0123456789abcdef"
PDF = b"%PDF-1.7\n" + b"x" * 100
CONFIG = ConfigArquivos(
    endpoint=ENDPOINT,
    bucket=BUCKET,
    chave_id="id-de-teste",
    chave_secreta="segredo-de-teste",
    # O moto só cria bucket com região de verdade; o R2 usa "auto".
    regiao="us-east-1",
)


@pytest.fixture(params=["falso", "s3"])
def arm(request):
    if request.param == "falso":
        yield ArmazenamentoFalso()
        return
    with mock_aws():
        s3 = ArmazenamentoS3(CONFIG)
        s3.cliente.create_bucket(Bucket=BUCKET)
        yield s3


def _receber(arm, chave: str, conteudo: bytes, tipo: str = "application/pdf") -> None:
    """O papel do navegador: o PUT na URL assinada."""
    if isinstance(arm, ArmazenamentoFalso):
        arm.receber(chave, conteudo, tipo)
    else:
        arm.cliente.put_object(
            Bucket=BUCKET, Key=f"envios/{chave}", Body=conteudo, ContentType=tipo
        )


def _publicado(arm, chave: str) -> tuple[bytes, str] | None:
    if isinstance(arm, ArmazenamentoFalso):
        return arm.objetos.get(f"arquivos/{chave}")
    try:
        objeto = arm.cliente.get_object(Bucket=BUCKET, Key=f"arquivos/{chave}")
    except arm.cliente.exceptions.NoSuchKey:
        return None
    return objeto["Body"].read(), objeto["ContentType"]


def _perto(momento: datetime, depois: timedelta) -> bool:
    return abs(momento - (datetime.now(UTC) + depois)) < timedelta(seconds=5)


# --- o que vale para os dois -------------------------------------------------------------------


def _etag(arm, chave: str = CHAVE) -> str:
    return arm.envio_recebido(chave).etag


def test_envio_que_nao_chegou_nao_tem_tamanho(arm):
    assert arm.envio_recebido(CHAVE) is None
    with pytest.raises(ObjetoAusente):
        arm.inicio_do_envio(CHAVE, etag='"qualquer"')


def test_tamanho_etag_e_inicio_do_envio(arm):
    _receber(arm, CHAVE, PDF)
    recebido = arm.envio_recebido(CHAVE)
    assert recebido.tamanho == len(PDF)
    assert recebido.etag == f'"{hashlib.md5(PDF).hexdigest()}"'
    assert arm.inicio_do_envio(CHAVE, 5, etag=recebido.etag) == b"%PDF-"
    assert arm.inicio_do_envio(CHAVE, etag=recebido.etag) == PDF[:16]


def test_inicio_de_arquivo_menor_que_o_pedido(arm):
    _receber(arm, CHAVE, b"%P")
    assert arm.inicio_do_envio(CHAVE, etag=_etag(arm)) == b"%P"


def test_inicio_do_envio_que_mudou_falha(arm):
    # Outro PUT na mesma URL depois do HEAD: o começo lido seria de outro conteúdo.
    _receber(arm, CHAVE, PDF)
    etag = _etag(arm)
    _receber(arm, CHAVE, b"MZ" + PDF[2:])
    with pytest.raises(EnvioMudou):
        arm.inicio_do_envio(CHAVE, etag=etag)


def test_publicar_copia_com_o_tipo_conferido(arm):
    _receber(arm, CHAVE, PDF, "image/jpeg")
    arm.publicar(CHAVE, "application/pdf", etag=_etag(arm))
    assert _publicado(arm, CHAVE) == (PDF, "application/pdf")


def test_publicar_de_novo_o_mesmo_conteudo_nao_falha(arm):
    # Tentativa anterior copiou e não gravou a linha: a seguinte vê arquivos/ e segue.
    _receber(arm, CHAVE, PDF)
    arm.publicar(CHAVE, "application/pdf", etag=_etag(arm))
    arm.publicar(CHAVE, "application/pdf", etag=_etag(arm))
    assert _publicado(arm, CHAVE) == (PDF, "application/pdf")


def test_publicar_por_cima_de_outro_conteudo_e_objeto_travado(arm):
    _receber(arm, CHAVE, PDF)
    arm.publicar(CHAVE, "application/pdf", etag=_etag(arm))
    _receber(arm, CHAVE, PDF + b"outro")
    with pytest.raises(ObjetoTravado):
        arm.publicar(CHAVE, "application/pdf", etag=_etag(arm))
    assert _publicado(arm, CHAVE) == (PDF, "application/pdf")


def test_descartar_so_mexe_no_envio(arm):
    outra = "f" * 32
    _receber(arm, outra, PDF)
    arm.publicar(outra, "application/pdf", etag=_etag(arm, outra))
    _receber(arm, CHAVE, PDF)
    arm.descartar_envio(CHAVE)
    arm.descartar_envio(CHAVE)  # de novo: nada acontece
    assert arm.envio_recebido(CHAVE) is None
    assert _publicado(arm, outra) == (PDF, "application/pdf")


@pytest.mark.parametrize(
    "chave", ["", "../arquivos/" + CHAVE, CHAVE.upper(), CHAVE + "0", "arquivos/" + CHAVE[:23]]
)
def test_chave_fora_do_formato_nunca_vira_caminho(arm, chave):
    for chamada in (
        lambda: arm.url_de_envio(chave, "application/pdf", 1),
        lambda: arm.url_de_leitura(chave, tipo="application/pdf", nome="a.pdf", baixar=False),
        lambda: arm.envio_recebido(chave),
        lambda: arm.inicio_do_envio(chave, etag='"x"'),
        lambda: arm.publicar(chave, "application/pdf", etag='"x"'),
        lambda: arm.descartar_envio(chave),
    ):
        with pytest.raises(ValueError, match="chave"):
            chamada()


def test_nao_existe_jeito_de_apagar_o_publicado():
    # A interface só tem `descartar_envio` (pasta envios/). ADR-0011.
    publicos = {n for n in dir(ArmazenamentoS3) if not n.startswith("_")}
    assert publicos == {
        "url_de_envio",
        "url_de_leitura",
        "envio_recebido",
        "inicio_do_envio",
        "publicar",
        "descartar_envio",
    }


def test_validades(arm):
    envio = arm.url_de_envio(CHAVE, "application/pdf", 1)
    leitura = arm.url_de_leitura(CHAVE, tipo="application/pdf", nome="a.pdf", baixar=False)
    assert _perto(envio.expira_em, timedelta(minutes=10))
    assert _perto(leitura.expira_em, timedelta(minutes=5))


# --- R2 (S3) -----------------------------------------------------------------------------------


@pytest.fixture
def s3():
    with mock_aws():
        arm = ArmazenamentoS3(CONFIG)
        arm.cliente.create_bucket(Bucket=BUCKET)
        yield arm


def _partes(url: str):
    partes = urlsplit(url)
    return partes, {k: v[0] for k, v in parse_qs(partes.query).items()}


def test_url_de_envio_e_put_em_envios_com_o_tipo_assinado(s3):
    url = s3.url_de_envio(CHAVE, "image/webp", 209).url
    partes, consulta = _partes(url)
    assert f"{partes.scheme}://{partes.netloc}" == ENDPOINT
    assert partes.path == f"/{BUCKET}/envios/{CHAVE}"
    assert consulta["X-Amz-Expires"] == "600"
    assert "content-type" in consulta["X-Amz-SignedHeaders"].split(";")


def test_url_de_envio_assina_o_tamanho_declarado(s3):
    # Sem o tamanho na assinatura, a mesma URL aceitaria GBs declarando 209 bytes.
    _, consulta = _partes(s3.url_de_envio(CHAVE, "application/pdf", 209).url)
    assert "content-length" in consulta["X-Amz-SignedHeaders"].split(";")


def test_url_de_leitura_forca_tipo_e_nome(s3):
    url = s3.url_de_leitura(CHAVE, tipo="application/pdf", nome="Ata de março", baixar=True).url
    partes, consulta = _partes(url)
    assert partes.path == f"/{BUCKET}/arquivos/{CHAVE}"
    assert consulta["X-Amz-Expires"] == "300"
    assert consulta["response-content-type"] == "application/pdf"
    assert consulta["response-content-disposition"] == disposicao(
        "Ata de março", "application/pdf", baixar=True
    )
    assert consulta["response-cache-control"] == "private, max-age=300"


def test_publicar_no_s3_se_o_envio_sumiu_e_objeto_ausente(s3):
    with pytest.raises(ObjetoAusente):
        s3.publicar(CHAVE, "application/pdf", etag='"x"')


def test_publicado_com_o_mesmo_etag_nao_e_copiado_de_novo(s3):
    # No R2, copiar por cima de arquivos/ travado falha sempre (era 500 permanente).
    copias = []
    s3.cliente.meta.events.register(
        "before-parameter-build.s3.CopyObject", lambda params, **_: copias.append(params)
    )
    _receber(s3, CHAVE, PDF)
    s3.publicar(CHAVE, "application/pdf", etag=_etag(s3))
    s3.publicar(CHAVE, "application/pdf", etag=_etag(s3))
    assert len(copias) == 1


def test_erro_do_bucket_vira_falha_no_armazenamento(s3):
    # Bucket que não existe (ou R2 fora do ar): nada de ClientError cru na rota.
    outro = ArmazenamentoS3(replace(CONFIG, bucket="bucket-que-nao-existe"))
    for chamada in (
        lambda: outro.inicio_do_envio(CHAVE, etag='"x"'),
        lambda: outro.publicar(CHAVE, "application/pdf", etag='"x"'),
        lambda: outro.descartar_envio(CHAVE),
    ):
        with pytest.raises(FalhaNoArmazenamento):
            chamada()


def test_publicar_no_s3_copia_so_se_o_envio_ainda_e_o_conferido(s3):
    # O moto ignora o CopySourceIfMatch; o R2 o respeita. Aqui, o pedido leva a condição.
    pedidos = []
    s3.cliente.meta.events.register(
        "before-parameter-build.s3.CopyObject", lambda params, **_: pedidos.append(dict(params))
    )
    _receber(s3, CHAVE, PDF)
    etag = _etag(s3)
    s3.publicar(CHAVE, "application/pdf", etag=etag)
    assert pedidos[0]["CopySourceIfMatch"] == etag


# --- falso -------------------------------------------------------------------------------------


def test_falso_imita_a_trava_de_arquivos():
    falso = ArmazenamentoFalso()
    falso.receber(CHAVE, PDF)
    falso.publicar(CHAVE, "application/pdf", etag=_etag(falso))
    falso.receber(CHAVE, b"outra coisa")
    with pytest.raises(ObjetoTravado):
        falso.publicar(CHAVE, "application/pdf", etag=_etag(falso))
    assert falso.objetos[f"arquivos/{CHAVE}"] == (PDF, "application/pdf")


def test_falso_nao_publica_envio_que_mudou():
    falso = ArmazenamentoFalso()
    falso.receber(CHAVE, PDF)
    etag = _etag(falso)
    falso.receber(CHAVE, b"MZ" + PDF[2:])
    with pytest.raises(EnvioMudou):
        falso.publicar(CHAVE, "application/pdf", etag=etag)
    assert f"arquivos/{CHAVE}" not in falso.objetos


def test_falso_recusa_put_de_tamanho_diferente_do_assinado():
    # Como o R2 com o Content-Length na assinatura: o PUT de outro tamanho não entra.
    falso = ArmazenamentoFalso()
    falso.url_de_envio(CHAVE, "application/pdf", len(PDF))
    with pytest.raises(EnvioRecusado):
        falso.receber(CHAVE, PDF + b"a mais")
    assert falso.objetos == {}
    falso.receber(CHAVE, PDF)
    assert falso.envio_recebido(CHAVE).tamanho == len(PDF)


def test_falso_monta_urls_reconheciveis():
    falso = ArmazenamentoFalso()
    assert falso.url_de_envio(CHAVE, "image/png", 1).url.startswith(
        f"https://armazenamento.falso/envios/{CHAVE}"
    )
    leitura = falso.url_de_leitura(CHAVE, tipo="image/png", nome="a.png", baixar=True).url
    assert leitura.startswith(f"https://armazenamento.falso/arquivos/{CHAVE}")
    assert "baixar=1" in leitura


# --- nome no download --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "tipo", "esperado"),
    [
        ("Regras da visita", "application/pdf", "Regras da visita.pdf"),
        ("Regras.PDF", "application/pdf", "Regras.PDF"),
        ("foto.jpeg", "image/jpeg", "foto.jpeg"),
        ("foto.JPG", "image/jpeg", "foto.JPG"),
        ("foto.jpg", "image/png", "foto.png"),
        ("foto.png", "image/webp", "foto.webp"),
        ("planta.v2", "application/pdf", "planta.v2.pdf"),
    ],
)
def test_nome_para_baixar_tem_a_extensao_do_tipo(nome, tipo, esperado):
    assert nome_para_baixar(nome, tipo) == esperado


def test_disposicao_com_nome_utf8_e_reserva_ascii():
    valor = disposicao('Ata de "março" nº 3', "application/pdf", baixar=True)
    assert valor.startswith("attachment; filename=\"Ata de _marco_ no 3.pdf\"; filename*=UTF-8''")
    assert unquote(valor.split("UTF-8''")[1]) == 'Ata de "março" nº 3.pdf'
    assert disposicao("a.pdf", "application/pdf", baixar=False).startswith("inline;")


def test_disposicao_sem_nada_ascii_usa_arquivo():
    assert 'filename="acao.pdf"' in disposicao("ação", "application/pdf", baixar=False)
    assert 'filename="arquivo.pdf"' in disposicao("日本", "application/pdf", baixar=False)


# --- dependência -------------------------------------------------------------------------------


def test_obter_armazenamento_sem_configuracao_e_none(monkeypatch):
    for nome in ("ENDPOINT", "BUCKET", "CHAVE_ID", "CHAVE_SECRETA"):
        monkeypatch.delenv(f"PORTAL_ARQUIVOS_{nome}", raising=False)
    configuracao.limpar_cache()
    assert armazenamento.obter_armazenamento() is None


def test_obter_armazenamento_com_configuracao_reaproveita_o_cliente(monkeypatch):
    monkeypatch.setenv("PORTAL_ARQUIVOS_ENDPOINT", ENDPOINT)
    monkeypatch.setenv("PORTAL_ARQUIVOS_BUCKET", BUCKET)
    monkeypatch.setenv("PORTAL_ARQUIVOS_CHAVE_ID", "id-de-teste")
    monkeypatch.setenv("PORTAL_ARQUIVOS_CHAVE_SECRETA", "segredo-de-teste")
    configuracao.limpar_cache()
    try:
        primeiro = armazenamento.obter_armazenamento()
        assert isinstance(primeiro, ArmazenamentoS3)
        assert armazenamento.obter_armazenamento() is primeiro
    finally:
        configuracao.limpar_cache()
