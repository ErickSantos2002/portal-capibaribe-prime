"""Correções da revisão de código dos classificados (provas A a G do revisor, M1 a M3 e B1 a B3).
Cada teste falhava antes do conserto."""

import threading

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.servicos.armazenamento import ArmazenamentoFalso, FalhaNoArmazenamento
from app.servicos.classificados import apagar_da_unidade
from testes.apoio import restricao
from testes.apoio_classificados import (
    JPEG,
    anunciar,
    criar_anuncio,
    criar_foto,
    envelhecer,
    enviar_foto,
    ids_da_lista,
    prender_foto,
)
from testes.conftest import ADMIN, COMISSAO, COMUM

SEGREDO = "segredo-da-revisao"
CRON = {"Authorization": f"Bearer {SEGREDO}"}


@pytest.fixture
def cron(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", SEGREDO)


def _fotos_no_bucket(armazenamento) -> list[str]:
    return [k for k in armazenamento.objetos if k.startswith("classificados/")]


# --- M2 (prova A): a foto copiada sem o commit não fica órfã -----------------------------------


def test_foto_copiada_mas_nao_confirmada_sai_do_bucket_na_faxina(
    cliente, logar, predio, cron, armazenamento, engine_superusuario, engine_app, monkeypatch
):
    dono = logar(COMUM)
    corpo = dono.post(
        "/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": len(JPEG)}
    ).json()
    chave = corpo["url"].split("/envios/")[1].split("?")[0]
    armazenamento.receber(chave, JPEG, "image/jpeg")
    original = ArmazenamentoFalso.publicar_foto

    def copia_e_cai(self, chave, tipo, *, etag):
        original(self, chave, tipo, etag=etag)
        raise FalhaNoArmazenamento("a resposta não voltou")

    monkeypatch.setattr(ArmazenamentoFalso, "publicar_foto", copia_e_cai)
    assert dono.post(f"/api/classificados/fotos/{corpo['foto_id']}/confirmar").status_code == 503
    monkeypatch.setattr(ArmazenamentoFalso, "publicar_foto", original)
    envelhecer(engine_superusuario, "anuncio_foto", "enviada_em", corpo["foto_id"], 2)
    assert cliente.get("/api/classificados/faxina", headers=CRON).status_code == 200
    with engine_app.connect() as con:
        assert con.execute(text("select count(*) from anuncio_foto")).scalar() == 0
    assert _fotos_no_bucket(armazenamento) == []


# --- B1 (provas B, C e D): o banco -------------------------------------------------------------


def test_app_nao_apaga_foto_que_nao_foi_descartada(logar, predio, armazenamento, engine_app):
    dono = logar(COMUM)
    presa = enviar_foto(dono, armazenamento)
    solta = enviar_foto(dono, armazenamento)
    anunciar(dono, fotos=[presa])
    for foto in (presa, solta):
        with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
            con.execute(text("delete from anuncio_foto where id = :f"), {"f": foto})
        assert restricao(erro.value) == "anuncio_foto_nao_descartada"


def test_banco_recusa_foto_nova_em_anuncio_vencido(
    engine_app, engine_superusuario, banco_limpo, ids
):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    envelhecer(engine_superusuario, "anuncio", "vence_em", a, 1)
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        prender_foto(con, criar_foto(con, ids["u"]), a, 0)
    assert restricao(erro.value) == "anuncio_foto_anuncio_fechado"


def test_escondido_por_sem_escondido_em_e_recusado(engine_app, banco_limpo, ids):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["u"])
    with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
        con.execute(
            text("update anuncio set escondido_por = :v where id = :a"), {"v": ids["v"], "a": a}
        )
    assert restricao(erro.value) == "anuncio_escondimento"


# --- M3 (prova E): o escondido sai em 7 dias ---------------------------------------------------


def test_faxina_apaga_escondido_ha_mais_de_7_dias(
    cliente, logar, predio, cron, armazenamento, engine_superusuario, engine_app
):
    dono = logar(COMUM)
    velho = anunciar(dono, fotos=[enviar_foto(dono, armazenamento)])
    recente = anunciar(dono, titulo="Escondido há pouco")
    for a in (velho, recente):
        assert logar(COMISSAO).post(f"/api/classificados/{a}/esconder").status_code == 204
    envelhecer(engine_superusuario, "anuncio", "escondido_em", velho, 8)
    envelhecer(engine_superusuario, "anuncio", "escondido_em", recente, 6)
    assert cliente.get("/api/classificados/faxina", headers=CRON).json()["anuncios"] == 1
    assert dono.get(f"/api/classificados/{velho}").status_code == 404
    assert dono.get(f"/api/classificados/{recente}").status_code == 200
    assert _fotos_no_bucket(armazenamento) == []


# --- B3 (prova F): o dono não avisa a gestão sobre o próprio anúncio ---------------------------


def test_dono_nao_avisa_o_proprio_anuncio(logar, predio, engine_app):
    dono = logar(COMUM)
    a = anunciar(dono)
    r = dono.post(f"/api/classificados/{a}/aviso", json={"motivo": "teste"})
    assert r.status_code == 409 and r.json()["codigo"] == "aviso_do_proprio"
    with engine_app.connect() as con:
        assert con.execute(text("select count(*) from aviso_anuncio")).scalar() == 0


# --- B2 (prova G): o anúncio criado no meio do "apagar meus dados" -----------------------------


def test_anuncio_criado_durante_apagar_meus_dados_e_recusado(engine_app, banco_limpo, ids):
    u = ids["u"]
    s1 = Session(engine_app)
    s1.execute(
        text("update unidade set precisa_trocar_senha = true, ativada_em = null where id = :u"),
        {"u": u},
    )
    apagar_da_unidade(s1, u)
    erros = []

    def outro_aparelho():
        try:
            with engine_app.begin() as con:
                criar_anuncio(con, u, titulo="Criado no meio")
        except DBAPIError as e:
            erros.append(restricao(e))

    t = threading.Thread(target=outro_aparelho)
    t.start()
    t.join(1.0)
    assert t.is_alive(), "o anúncio novo devia esperar a trava da unidade"
    s1.commit()
    t.join(5)
    assert erros == ["classificado_de_unidade_inativa"]
    with engine_app.connect() as con:
        assert (
            con.execute(
                text("select count(*) from anuncio where unidade_id = :u"), {"u": u}
            ).scalar()
            == 0
        )


def test_unidade_que_precisa_trocar_a_senha_nao_anuncia_envia_foto_nem_avisa(
    engine_app, engine_dono, banco_limpo, ids
):
    with engine_app.begin() as con:
        a = criar_anuncio(con, ids["v"])
    with engine_dono.begin() as con:
        con.execute(
            text("update unidade set precisa_trocar_senha = true where id = :u"), {"u": ids["u"]}
        )
    for comando in (
        lambda con: criar_anuncio(con, ids["u"]),
        lambda con: criar_foto(con, ids["u"]),
        lambda con: con.execute(
            text("insert into aviso_anuncio (anuncio_id, unidade_id) values (:a, :u)"),
            {"a": a, "u": ids["u"]},
        ),
    ):
        with pytest.raises(DBAPIError) as erro, engine_app.begin() as con:
            comando(con)
        assert restricao(erro.value) == "classificado_de_unidade_inativa"


# --- UX 5, 11, 12 e 3 (API) --------------------------------------------------------------------


def test_gestao_no_proprio_anuncio_ve_a_visao_do_dono(logar, predio):
    admin = logar(ADMIN)
    meu = anunciar(admin, titulo="Do admin")
    alheio = anunciar(logar(COMUM), titulo="Do vizinho")
    for a in (meu, alheio):
        logar(COMISSAO).post(f"/api/classificados/{a}/aviso")
    assert admin.get(f"/api/classificados/{meu}").json()["avisos"] is None
    assert admin.get(f"/api/classificados/{alheio}").json()["avisos"] is not None
    lista = admin.get("/api/classificados").json()
    # O contador e o filtro "com aviso" não contam os da própria unidade.
    assert lista["com_aviso"] == 1
    assert ids_da_lista(admin, com_aviso=True) == [alheio]
    assert {i["id"]: i["avisos_abertos"] for i in lista["itens"]}[meu] is None


def test_meus_abertos_e_vence_em_no_cartao(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    aberto = anunciar(dono, titulo="Aberto")
    vencido = anunciar(dono, titulo="Vencido")
    encerrado = anunciar(dono, titulo="Encerrado")
    envelhecer(engine_superusuario, "anuncio", "vence_em", vencido, 1)
    dono.post(f"/api/classificados/{encerrado}/encerrar", json={"motivo": "vendi"})
    lista = dono.get("/api/classificados").json()
    assert (lista["meus"], lista["meus_abertos"]) == (3, 1)
    cartao = next(
        i for i in dono.get("/api/classificados/meus").json()["itens"] if i["id"] == aberto
    )
    assert cartao["vence_em"]


def test_meus_avisa_o_limite_antes_do_publicar(logar, predio):
    dono = logar(COMUM)
    assert dono.get("/api/classificados/meus").json()["limite"] is None
    for n in range(5):
        anunciar(dono, titulo=f"Coisa número {n}")
    assert dono.get("/api/classificados/meus").json()["limite"] == (
        "Seu apartamento já fez 5 anúncios hoje. Tente de novo amanhã."
    )


def test_busca_das_indicacoes_por_palavras_soltas_em_qualquer_ordem(logar, predio):
    from testes.apoio_indicacoes import ids_da_lista as indicacoes
    from testes.apoio_indicacoes import indicar

    p = indicar(logar(COMUM), nome="Marcenaria Silva", comentario="Fez a cozinha no prazo.")
    leitor = logar(ADMIN)
    assert indicacoes(leitor, busca="cozinha silva") == [p]
    assert indicacoes(leitor, busca="MOVEIS marcenaria") == [p]
    assert indicacoes(leitor, busca="silva eletrica") == []


def test_busca_por_palavras_soltas_em_qualquer_ordem(logar, predio):
    a = anunciar(logar(COMUM), titulo="Sofá de 3 lugares cinza")
    anunciar(logar(COMUM), titulo="Mesa cinza", descricao=None)
    leitor = logar(ADMIN)
    assert ids_da_lista(leitor, busca="cinza sofa") == [a]
    assert ids_da_lista(leitor, busca="SOFÁ   lugares") == [a]
    assert ids_da_lista(leitor, busca="sofa azul") == []
