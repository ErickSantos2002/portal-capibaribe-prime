"""As fotos dos classificados (ADR-0012): a pasta `classificados/`, sem trava, o envio pela API e
o descartar e varrer."""

import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

ENDPOINT = "https://conta-ficticia.r2.cloudflarestorage.com"
os.environ.setdefault("MOTO_S3_CUSTOM_ENDPOINTS", ENDPOINT)

from moto import mock_aws  # noqa: E402

from app.configuracao import ConfigArquivos  # noqa: E402
from app.modelos.classificados import AnuncioFoto  # noqa: E402
from app.servicos import classificados_fotos  # noqa: E402
from app.servicos.armazenamento import (  # noqa: E402
    ArmazenamentoFalso,
    ArmazenamentoS3,
    FalhaNoArmazenamento,
)
from testes.apoio_classificados import JPEG, PDF, PNG, enviar_foto  # noqa: E402
from testes.conftest import COMUM  # noqa: E402

BUCKET = "portal-capibaribe-arquivos"
CHAVE = "0123456789abcdef0123456789abcdef"
CONFIG = ConfigArquivos(
    endpoint=ENDPOINT,
    bucket=BUCKET,
    chave_id="id-de-teste",
    chave_secreta="segredo-de-teste",
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


def _receber(arm, chave: str, conteudo: bytes, tipo: str) -> None:
    if isinstance(arm, ArmazenamentoFalso):
        arm.receber(chave, conteudo, tipo)
    else:
        arm.cliente.put_object(
            Bucket=BUCKET, Key=f"envios/{chave}", Body=conteudo, ContentType=tipo
        )


def _existe(arm, caminho: str) -> bool:
    if isinstance(arm, ArmazenamentoFalso):
        return caminho in arm.objetos
    try:
        arm.cliente.head_object(Bucket=BUCKET, Key=caminho)
    except arm.cliente.exceptions.ClientError:
        return False
    return True


# --- a camada de armazenamento ----------------------------------------------------------------


def test_publicar_foto_copia_para_classificados_e_nunca_para_arquivos(arm):
    _receber(arm, CHAVE, JPEG, "image/jpeg")
    arm.publicar_foto(CHAVE, "image/jpeg", etag=arm.envio_recebido(CHAVE).etag)
    assert _existe(arm, f"classificados/{CHAVE}")
    assert not _existe(arm, f"arquivos/{CHAVE}")


def test_apagar_classificado_apaga_e_repetir_nao_falha(arm):
    _receber(arm, CHAVE, JPEG, "image/jpeg")
    arm.publicar_foto(CHAVE, "image/jpeg", etag=arm.envio_recebido(CHAVE).etag)
    arm.apagar_classificado(f"classificados/{CHAVE}")
    assert not _existe(arm, f"classificados/{CHAVE}")
    arm.apagar_classificado(f"classificados/{CHAVE}")


@pytest.mark.parametrize(
    "caminho",
    [
        f"arquivos/{CHAVE}",
        f"envios/{CHAVE}",
        CHAVE,
        f"classificados/{CHAVE}/../arquivos/{CHAVE}",
        f"classificados/../arquivos/{CHAVE}",
        f"/classificados/{CHAVE}",
        f"classificados/{CHAVE.upper()}",
        "classificados/",
        f"classificados/{CHAVE}x",
    ],
)
def test_apagar_classificado_recusa_fora_da_pasta(arm, caminho):
    # Nem pede ao bucket: recusa antes.
    if isinstance(arm, ArmazenamentoFalso):
        arm.objetos[f"arquivos/{CHAVE}"] = (b"%PDF", "application/pdf")
    with pytest.raises(ValueError, match="classificados"):
        arm.apagar_classificado(caminho)
    if isinstance(arm, ArmazenamentoFalso):
        assert f"arquivos/{CHAVE}" in arm.objetos


def test_url_da_foto_e_get_em_classificados():
    with mock_aws():
        s3 = ArmazenamentoS3(CONFIG)
        url = s3.url_da_foto(CHAVE, tipo="image/webp").url
    assert f"/{BUCKET}/classificados/{CHAVE}?" in url
    assert "response-content-type=image%2Fwebp" in url


# --- o envio pela API -------------------------------------------------------------------------


def _foto(engine, foto_id: int):
    with Session(engine) as db:
        return db.get(AnuncioFoto, foto_id)


def test_enviar_e_confirmar_guarda_em_classificados(logar, predio, armazenamento, engine_app):
    foto = enviar_foto(logar(COMUM), armazenamento, PNG, "image/png")
    linha = _foto(engine_app, foto)
    assert linha.confirmada_em is not None and linha.tipo == "image/png"
    assert f"classificados/{linha.chave}" in armazenamento.objetos
    assert f"arquivos/{linha.chave}" not in armazenamento.objetos
    # O envio é apagado depois da cópia.
    assert f"envios/{linha.chave}" not in armazenamento.objetos


def test_qualquer_unidade_envia_foto(logar, predio, armazenamento):
    # O /api/arquivos é só da gestão; a foto do classificado é de qualquer unidade logada.
    r = logar(COMUM).post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": 9}
    )
    assert r.status_code == 201
    assert "/envios/" in r.json()["url"]


@pytest.mark.parametrize("conteudo", [PDF, b"MZ" + b"0" * 60])
def test_conteudo_que_nao_e_foto_e_recusado_e_conta_no_limite(
    logar, predio, armazenamento, engine_app, conteudo
):
    cliente = logar(COMUM)
    pedido = cliente.post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": len(conteudo)}
    ).json()
    chave = pedido["url"].split("/envios/")[1].split("?")[0]
    armazenamento.receber(chave, conteudo, "image/jpeg")
    r = cliente.post(f"/api/classificados/fotos/{pedido['foto_id']}/confirmar")
    assert r.status_code == 422 and r.json()["codigo"] == "foto_recusada"
    linha = _foto(engine_app, pedido["foto_id"])
    assert linha is not None and linha.descartada_em is not None
    assert f"envios/{chave}" not in armazenamento.objetos
    assert not any(k.startswith("classificados/") for k in armazenamento.objetos)


def test_pdf_nem_e_pedido(logar, predio, armazenamento):
    r = logar(COMUM).post(
        "/api/classificados/fotos", json={"tipo": "application/pdf", "tamanho_bytes": 9}
    )
    assert r.status_code == 422
    assert r.json()["mensagem"] == "O Portal aceita fotos em JPEG, PNG ou WEBP."


def test_foto_de_outra_unidade_nao_e_confirmada(logar, predio, armazenamento):
    pedido = (
        logar(COMUM)
        .post("/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": len(JPEG)})
        .json()
    )
    r = logar("2304").post(f"/api/classificados/fotos/{pedido['foto_id']}/confirmar")
    assert r.status_code == 404


def test_foto_que_nao_chegou_continua_pendente(logar, predio, armazenamento, engine_app):
    cliente = logar(COMUM)
    pedido = cliente.post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": len(JPEG)}
    ).json()
    r = cliente.post(f"/api/classificados/fotos/{pedido['foto_id']}/confirmar")
    assert r.status_code == 409 and r.json()["codigo"] == "arquivo_nao_chegou"
    assert _foto(engine_app, pedido["foto_id"]).descartada_em is None


def test_arquivos_desligados_503(logar, predio):
    r = logar(COMUM).post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": 9}
    )
    assert r.status_code == 503 and r.json()["codigo"] == "arquivos_desligados"


def test_limite_de_fotos_do_dia_vira_429(logar, predio, armazenamento, engine_app):
    with engine_app.begin() as con:
        for n in range(40):
            con.execute(
                text(
                    "insert into anuncio_foto (unidade_id, chave, tipo, bytes)"
                    " values (:u, :k, 'image/jpeg', 9)"
                ),
                {"u": predio[COMUM], "k": f"{n:032x}"},
            )
    r = logar(COMUM).post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": 9}
    )
    assert r.status_code == 429 and r.json()["codigo"] == "limite_do_dia"


# --- descartar e varrer -----------------------------------------------------------------------


def test_varrer_apaga_o_objeto_e_so_a_linha_velha(
    logar, predio, armazenamento, engine_app, engine_superusuario
):
    nova = enviar_foto(logar(COMUM), armazenamento)
    velha = enviar_foto(logar(COMUM), armazenamento)
    with engine_superusuario.begin() as con:
        con.execute(text("alter table anuncio_foto disable trigger user"))
        con.execute(
            text("update anuncio_foto set enviada_em = now() - interval '2 days' where id = :f"),
            {"f": velha},
        )
        con.execute(text("alter table anuncio_foto enable trigger user"))
    with Session(engine_app) as db:
        assert sorted(classificados_fotos.descartar(db, AnuncioFoto.id.in_([nova, velha]))) == [
            nova,
            velha,
        ]
        db.commit()
        assert classificados_fotos.varrer(db, armazenamento) == 1
    assert not any(k.startswith("classificados/") for k in armazenamento.objetos)
    with Session(engine_app) as db:
        restantes = list(db.scalars(select(AnuncioFoto.id)))
    # A nova fica, descartada, para contar no limite do dia.
    assert restantes == [nova]


def test_varrer_com_o_bucket_falhando_nao_levanta_e_guarda_para_a_faxina(
    logar, predio, armazenamento, engine_app, monkeypatch
):
    foto = enviar_foto(logar(COMUM), armazenamento)

    def falhar(caminho):
        raise FalhaNoArmazenamento(caminho)

    monkeypatch.setattr(armazenamento, "apagar_classificado", falhar)
    with Session(engine_app) as db:
        classificados_fotos.descartar(db, AnuncioFoto.id == foto)
        db.commit()
        assert classificados_fotos.varrer(db, armazenamento, apagar_linhas=True) == 0
    assert _foto(engine_app, foto) is not None
    assert any(k.startswith("classificados/") for k in armazenamento.objetos)


def test_varrer_sem_bucket_nao_faz_nada(engine_app, banco_limpo):
    with Session(engine_app) as db:
        assert classificados_fotos.varrer(db, None) == 0
