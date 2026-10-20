"""A faxina diária e o "apagar meus dados"/reset dos classificados (spec de 20/10/2026, seções 6
e 7; ADR-0012): anúncio, avisos e fotos apagados de verdade, inclusive no bucket."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modelos.classificados import Anuncio, AnuncioFoto, AvisoAnuncio
from app.servicos.armazenamento import FalhaNoArmazenamento
from testes.apoio_classificados import anunciar, envelhecer, enviar_foto
from testes.conftest import ADMIN, COMISSAO, COMUM

SEGREDO = "segredo-do-cron-de-teste"
CRON = {"Authorization": f"Bearer {SEGREDO}"}


@pytest.fixture
def cron(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", SEGREDO)


def _contar(engine, modelo) -> int:
    with Session(engine) as db:
        return db.scalar(select(func.count()).select_from(modelo))


def _fotos_no_bucket(armazenamento) -> list[str]:
    return sorted(k for k in armazenamento.objetos if k.startswith("classificados/"))


def _faxinar(cliente):
    r = cliente.get("/api/classificados/faxina", headers=CRON)
    assert r.status_code == 200, r.text
    return r.json()


# --- quem pode rodar --------------------------------------------------------------------------


def test_sem_cron_secret_503_e_nada_roda(cliente, predio, monkeypatch):
    monkeypatch.delenv("CRON_SECRET", raising=False)
    r = cliente.get("/api/classificados/faxina", headers=CRON)
    assert r.status_code == 503 and r.json()["codigo"] == "faxina_desligada"


@pytest.mark.parametrize(
    "cabecalho", [{}, {"Authorization": "Bearer outro"}, {"Authorization": SEGREDO}]
)
def test_segredo_errado_401(cliente, predio, cron, cabecalho):
    assert cliente.get("/api/classificados/faxina", headers=cabecalho).status_code == 401


def test_logado_sem_o_segredo_tambem_nao_roda(logar, predio, cron):
    assert logar(ADMIN).get("/api/classificados/faxina").status_code == 401


# --- o que sai --------------------------------------------------------------------------------


def test_apaga_vencido_ha_30_dias_e_encerrado_ha_7_com_avisos_e_fotos(
    cliente, logar, predio, cron, armazenamento, engine_app, engine_superusuario
):
    dono = logar(COMUM)
    vencido = anunciar(dono, titulo="Vencido há muito", fotos=[enviar_foto(dono, armazenamento)])
    vencido_recente = anunciar(dono, titulo="Vencido há pouco")
    encerrado = anunciar(
        dono, titulo="Encerrado há muito", fotos=[enviar_foto(dono, armazenamento)]
    )
    encerrado_recente = anunciar(dono, titulo="Encerrado há pouco")
    aberto = anunciar(dono, titulo="Aberto", fotos=[enviar_foto(dono, armazenamento)])
    logar(COMISSAO).post(f"/api/classificados/{vencido}/aviso")
    envelhecer(engine_superusuario, "anuncio", "vence_em", vencido, 31)
    envelhecer(engine_superusuario, "anuncio", "vence_em", vencido_recente, 29)
    for a in (encerrado, encerrado_recente):
        dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "vendi"})
    envelhecer(engine_superusuario, "anuncio", "encerrado_em", encerrado, 8)
    envelhecer(engine_superusuario, "anuncio", "encerrado_em", encerrado_recente, 6)
    # As fotos foram enviadas "há 2 dias": a linha sai junto.
    with engine_superusuario.begin() as con:
        con.execute(text("alter table anuncio_foto disable trigger user"))
        con.execute(text("update anuncio_foto set enviada_em = now() - interval '2 days'"))
        con.execute(text("alter table anuncio_foto enable trigger user"))

    assert _faxinar(cliente) == {"anuncios": 2, "fotos": 2}
    with Session(engine_app) as db:
        restantes = set(db.scalars(select(Anuncio.id)))
    assert restantes == {vencido_recente, encerrado_recente, aberto}
    assert _contar(engine_app, AvisoAnuncio) == 0
    assert _contar(engine_app, AnuncioFoto) == 1
    assert len(_fotos_no_bucket(armazenamento)) == 1
    with engine_app.connect() as con:
        detalhes = con.execute(
            text("select detalhes from historico where acao = 'classificados_faxina'")
        ).scalar_one()
    assert detalhes == {"anuncios": 2, "fotos": 2}
    # De novo, no mesmo dia: nada a mais, e nada vai para o histórico.
    assert _faxinar(cliente) == {"anuncios": 0, "fotos": 0}
    with engine_app.connect() as con:
        assert (
            con.execute(
                text("select count(*) from historico where acao = 'classificados_faxina'")
            ).scalar_one()
            == 1
        )


def test_foto_esquecida_ha_mais_de_1_dia_sai_e_a_de_hoje_fica(
    cliente, logar, predio, cron, armazenamento, engine_app, engine_superusuario
):
    dono = logar(COMUM)
    esquecida = enviar_foto(dono, armazenamento)
    de_hoje = enviar_foto(dono, armazenamento)
    pendente = dono.post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": 9}
    ).json()["foto_id"]
    with engine_superusuario.begin() as con:
        con.execute(text("alter table anuncio_foto disable trigger user"))
        con.execute(
            text(
                "update anuncio_foto set enviada_em = now() - interval '2 days'"
                " where id in (:a, :b)"
            ),
            {"a": esquecida, "b": pendente},
        )
        con.execute(text("alter table anuncio_foto enable trigger user"))
    assert _faxinar(cliente)["fotos"] == 2
    with Session(engine_app) as db:
        assert list(db.scalars(select(AnuncioFoto.id))) == [de_hoje]
    assert len(_fotos_no_bucket(armazenamento)) == 1


def test_bucket_falhando_nao_quebra_e_a_proxima_rodada_termina(
    cliente, logar, predio, cron, armazenamento, engine_app, engine_superusuario, monkeypatch
):
    dono = logar(COMUM)
    a = anunciar(dono, fotos=[enviar_foto(dono, armazenamento)])
    dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "doei"})
    envelhecer(engine_superusuario, "anuncio", "encerrado_em", a, 8)
    original = armazenamento.apagar_classificado

    def falhar(caminho):
        raise FalhaNoArmazenamento(caminho)

    monkeypatch.setattr(armazenamento, "apagar_classificado", falhar)
    assert _faxinar(cliente)["anuncios"] == 1
    assert _contar(engine_app, Anuncio) == 0
    assert len(_fotos_no_bucket(armazenamento)) == 1
    monkeypatch.setattr(armazenamento, "apagar_classificado", original)
    _faxinar(cliente)
    assert _fotos_no_bucket(armazenamento) == []


# --- "apagar meus dados" e reset --------------------------------------------------------------

APAGAR = {"senha": f"senha-{COMUM}", "confirmo": True}


@pytest.mark.parametrize("como", ["apagar meus dados", "reset"])
def test_apagar_leva_anuncios_fotos_e_avisos_da_unidade(
    logar, predio, armazenamento, engine_app, como
):
    dono = logar(COMUM)
    com_foto = anunciar(dono, fotos=[enviar_foto(dono, armazenamento)])
    enviar_foto(dono, armazenamento)  # pronta, ainda sem anúncio
    dono.post(f"/api/classificados/{com_foto}/aviso")  # avisou sobre o próprio
    alheio = anunciar(logar(ADMIN), titulo="Do vizinho")
    dono.post(f"/api/classificados/{alheio}/aviso", json={"motivo": "Teste"})
    logar(COMISSAO).post(f"/api/classificados/{com_foto}/aviso")
    if como == "reset":
        r = logar(ADMIN).post(f"/api/admin/unidades/{COMUM}/resetar", json={"confirmo": True})
        assert r.status_code == 200, r.text
    else:
        r = dono.post("/api/minha-unidade/apagar-dados", json=APAGAR)
        assert r.status_code == 204, r.text
    with Session(engine_app) as db:
        assert list(db.scalars(select(Anuncio.id))) == [alheio]
        assert db.scalar(select(func.count()).select_from(AnuncioFoto)) == 0
        assert db.scalar(select(func.count()).select_from(AvisoAnuncio)) == 0
    assert _fotos_no_bucket(armazenamento) == []
