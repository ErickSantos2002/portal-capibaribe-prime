"""Épico A do M3 · achados das revisões independentes (código e UX) sobre os documentos.

C1/C2: número fora do tipo do banco não vira 500. C3: título sem caractere invisível. C4: a
resposta da nova versão é a versão que este pedido criou. U1: publicar de novo o mesmo arquivo
(a resposta se perdeu) leva ao que já foi publicado, sem duplicar. U3/U13: aviso da nova versão
e linha opcional no aviso. U7: "abrir" pelo Portal, que confere o acesso e redireciona para um
link novo a cada vez.
"""

import pytest
from sqlalchemy import text

from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_documentos_apoio import corpo, enviar_arquivo, nova_versao, publicar_documento

pytestmark = pytest.mark.usefixtures("predio", "armazenamento")

GRANDE = 2**63  # um a mais que o maior bigint
SMALLINT = 32768  # um a mais que o maior smallint


def _contar(engine, tabela: str) -> int:
    with engine.connect() as con:
        return con.execute(text(f"select count(*) from {tabela}")).scalar_one()  # noqa: S608


@pytest.fixture
def agendados(monkeypatch) -> list[int]:
    from app.rotas import documentos

    chamados: list[int] = []
    monkeypatch.setattr(
        documentos.notificacoes, "agendar", lambda _tarefas, aviso_id: chamados.append(aviso_id)
    )
    return chamados


# --- C1, C2: números fora do tipo do banco -----------------------------------------------------


@pytest.mark.parametrize(
    "caminho",
    [
        f"/api/documentos/1/versoes/{SMALLINT}/link",
        f"/api/documentos/1/versoes/{SMALLINT}/abrir",
        f"/api/documentos/{GRANDE}/versoes/1/link",
        f"/api/documentos/{GRANDE}/versoes/1/abrir",
        "/api/documentos/1/versoes/0/link",
        "/api/documentos/0/versoes/1/link",
    ],
)
def test_numero_fora_do_banco_sem_sessao_nao_e_500(cliente, caminho):
    resposta = cliente.get(caminho, follow_redirects=False)
    assert resposta.status_code == 422, resposta.text
    assert resposta.json()["codigo"] == "dados_invalidos"


def test_numero_fora_do_banco_nas_rotas_da_gestao(logar):
    comissao = logar(COMISSAO)
    respostas = [
        comissao.get(f"/api/documentos/{GRANDE}"),
        comissao.post(f"/api/documentos/{GRANDE}/arquivar"),
        comissao.post(f"/api/documentos/{GRANDE}/versoes", json={"arquivo_id": 1}),
        comissao.post("/api/documentos/1/versoes", json={"arquivo_id": GRANDE}),
        comissao.post("/api/documentos", json=corpo(GRANDE)),
        comissao.post("/api/documentos", json=corpo(0)),
    ]
    assert [r.status_code for r in respostas] == [422] * len(respostas)


# --- C3: título sem caractere invisível --------------------------------------------------------


@pytest.mark.parametrize(
    "invisivel",
    [" ", " ", "ㅤ", "ﾠ", "ᅟ", "ᅠ", "؜", "᠎", "­"],
)
def test_titulo_recusa_invisivel(logar, invisivel):
    resposta = logar(COMISSAO).post(
        "/api/documentos", json=corpo(1, titulo=f"Ata{invisivel}de outubro")
    )
    assert resposta.status_code == 422
    assert {c["campo"] for c in resposta.json()["campos"]} == {"titulo"}


def test_titulo_so_com_invisivel_e_recusado(logar):
    resposta = logar(COMISSAO).post("/api/documentos", json=corpo(1, titulo="ㅤㅤ"))
    assert resposta.status_code == 422


def test_titulo_com_emoji_composto_continua_valendo(logar, armazenamento):
    # O ZWJ (U+200D) junta os emojis de família e de profissão; a regra comum já o aceita.
    documento = publicar_documento(logar, armazenamento, titulo="Obra 👷‍♀️ e prazos")
    assert documento["titulo"] == "Obra 👷‍♀️ e prazos"


# --- C4: a resposta é a versão criada por este pedido ------------------------------------------


def test_nova_versao_responde_a_versao_que_criou(logar, armazenamento, engine_app, monkeypatch):
    from app.servicos import documentos as servico

    publicado = publicar_documento(logar, armazenamento)
    comissao = logar(COMISSAO)
    deste = enviar_arquivo(comissao, armazenamento, nome="Deste pedido.pdf")
    do_outro = enviar_arquivo(comissao, armazenamento, nome="Do outro pedido.pdf")
    original = servico.nova_versao

    def com_outro_pedido_logo_depois(db, logado, documento_id, dados):
        criada = original(db, logado, documento_id, dados)
        # Outro pedido grava a versão seguinte entre o commit deste e a resposta.
        with engine_app.begin() as con:
            con.execute(
                text(
                    "insert into documento_versao (documento_id, versao, arquivo_id, enviada_por)"
                    " select :d, 3, :a, enviado_por from arquivo where id = :a"
                ),
                {"d": documento_id, "a": do_outro},
            )
        return criada

    monkeypatch.setattr(servico, "nova_versao", com_outro_pedido_logo_depois)
    resposta = comissao.post(
        f"/api/documentos/{publicado['id']}/versoes", json={"arquivo_id": deste}
    )
    assert resposta.status_code == 201, resposta.text
    documento = resposta.json()
    assert documento["versao"] == 2
    assert documento["arquivo"]["nome"] == "Deste pedido.pdf"
    assert [v["versao"] for v in documento["versoes_anteriores"]] == [1]


# --- U1: a resposta se perdeu e a tela manda de novo -------------------------------------------


def test_publicar_de_novo_o_mesmo_arquivo_leva_ao_publicado(
    logar, armazenamento, engine_app, agendados
):
    comissao = logar(COMISSAO)
    arquivo_id = enviar_arquivo(comissao, armazenamento)
    primeiro = comissao.post("/api/documentos", json=corpo(arquivo_id, avisar_unidades=True))
    assert primeiro.status_code == 201
    segundo = comissao.post("/api/documentos", json=corpo(arquivo_id, avisar_unidades=True))
    assert segundo.status_code == 409
    assert segundo.json()["codigo"] == "arquivo_em_uso"
    assert segundo.json()["documento_id"] == primeiro.json()["id"]
    assert segundo.json()["versao"] == 1
    assert _contar(engine_app, "documento") == 1
    assert _contar(engine_app, "aviso") == 1
    assert len(agendados) == 1


def test_nova_versao_de_novo_com_o_mesmo_arquivo_leva_a_ela(logar, armazenamento, engine_app):
    publicado = publicar_documento(logar, armazenamento)
    comissao = logar(COMISSAO)
    arquivo_id = enviar_arquivo(comissao, armazenamento, nome="v2.pdf")
    caminho = f"/api/documentos/{publicado['id']}/versoes"
    assert comissao.post(caminho, json={"arquivo_id": arquivo_id}).status_code == 201
    de_novo = comissao.post(caminho, json={"arquivo_id": arquivo_id})
    assert de_novo.status_code == 409
    assert de_novo.json()["documento_id"] == publicado["id"]
    assert de_novo.json()["versao"] == 2
    assert _contar(engine_app, "documento_versao") == 2


# --- U3: aviso da nova versão ------------------------------------------------------------------


def test_nova_versao_sem_aviso_por_padrao(logar, armazenamento, engine_app, agendados):
    publicado = publicar_documento(logar, armazenamento)
    nova_versao(logar, armazenamento, publicado["id"])
    assert _contar(engine_app, "aviso") == 0
    assert agendados == []


def test_nova_versao_avisando_com_o_que_mudou(logar, armazenamento, agendados, monkeypatch):
    monkeypatch.setenv("PORTAL_URL_BASE", "https://portal.exemplo.test")
    publicado = publicar_documento(
        logar, armazenamento, titulo="Cronograma da obra", categoria="obra"
    )
    comissao = logar(COMISSAO)
    arquivo_id = enviar_arquivo(comissao, armazenamento)
    resposta = comissao.post(
        f"/api/documentos/{publicado['id']}/versoes",
        json={
            "arquivo_id": arquivo_id,
            "avisar_unidades": True,
            "nota_do_aviso": "  A entrega das chaves passou para março.  ",
        },
    )
    assert resposta.status_code == 201, resposta.text
    [aviso_id] = agendados
    aviso = logar(COMUM).get(f"/api/avisos/{aviso_id}").json()
    assert aviso["titulo"] == "Documento atualizado: Cronograma da obra"
    assert aviso["categoria"] == "obra"
    assert aviso["texto"] == (
        "Saiu a versão 2 de um documento do Portal: “Cronograma da obra”.\n\n"
        "A entrega das chaves passou para março.\n\n"
        "Ela fica guardada em Documentos, no menu do Portal: "
        f"https://portal.exemplo.test/documentos/{publicado['id']}"
    )


def test_nova_versao_sem_endereco_do_portal_nao_poe_link(logar, armazenamento, agendados):
    publicado = publicar_documento(logar, armazenamento, titulo="Regimento", categoria="regimento")
    comissao = logar(COMISSAO)
    arquivo_id = enviar_arquivo(comissao, armazenamento)
    comissao.post(
        f"/api/documentos/{publicado['id']}/versoes",
        json={"arquivo_id": arquivo_id, "avisar_unidades": True},
    )
    [aviso_id] = agendados
    aviso = logar(COMUM).get(f"/api/avisos/{aviso_id}").json()
    assert aviso["categoria"] == "geral"
    assert aviso["texto"] == (
        "Saiu a versão 2 de um documento do Portal: “Regimento”.\n\n"
        "Ela fica guardada em Documentos, no menu do Portal."
    )


def test_nova_versao_de_documento_da_gestao_nao_avisa(logar, armazenamento, engine_app):
    publicado = publicar_documento(logar, armazenamento, acesso="gestao")
    comissao = logar(COMISSAO)
    arquivo_id = enviar_arquivo(comissao, armazenamento)
    resposta = comissao.post(
        f"/api/documentos/{publicado['id']}/versoes",
        json={"arquivo_id": arquivo_id, "avisar_unidades": True},
    )
    assert resposta.status_code == 422
    assert resposta.json()["mensagem"] == (
        "Só dá para avisar as unidades de documento que elas podem ver."
    )
    assert _contar(engine_app, "documento_versao") == 1


@pytest.mark.parametrize(
    ("nota", "mensagem"),
    [
        ("x" * 301, "A linha do aviso pode ter até 300 letras."),
        ("linha‮oculta", None),
    ],
)
def test_nota_do_aviso_confere(logar, nota, mensagem):
    resposta = logar(COMISSAO).post(
        "/api/documentos", json=corpo(1, avisar_unidades=True, nota_do_aviso=nota)
    )
    assert resposta.status_code == 422
    assert {c["campo"] for c in resposta.json()["campos"]} == {"nota_do_aviso"}
    if mensagem:
        assert resposta.json()["mensagem"] == mensagem


# --- U13: linha opcional e categoria do aviso do documento novo --------------------------------


@pytest.mark.parametrize(
    ("categoria", "do_aviso"),
    [("obra", "obra"), ("ata", "reuniao"), ("contrato", "geral"), ("convencao", "geral")],
)
def test_aviso_do_documento_novo_com_a_categoria_coerente(
    logar, armazenamento, agendados, categoria, do_aviso
):
    documento = publicar_documento(
        logar, armazenamento, categoria=categoria, avisar_unidades=True, titulo="Doc"
    )
    aviso = logar(COMUM).get(f"/api/avisos/{documento['aviso_id']}").json()
    assert aviso["categoria"] == do_aviso


def test_aviso_do_documento_novo_com_a_linha_da_gestao(logar, armazenamento, agendados):
    documento = publicar_documento(
        logar,
        armazenamento,
        titulo="Regimento interno",
        avisar_unidades=True,
        nota_do_aviso="Leiam até sexta, a votação é no sábado.",
    )
    aviso = logar(COMUM).get(f"/api/avisos/{documento['aviso_id']}").json()
    assert aviso["texto"] == (
        "Um documento novo foi publicado no Portal: “Regimento interno”.\n\n"
        "Leiam até sexta, a votação é no sábado.\n\n"
        "Ele fica guardado em Documentos, no menu do Portal, e o botão “Ver o documento”"
        " deste aviso leva direto a ele."
    )


# --- U7: abrir pelo Portal, com link novo a cada vez -------------------------------------------


def _abrir(quem, documento_id: int, versao: int = 1, baixar: bool = False):
    caminho = f"/api/documentos/{documento_id}/versoes/{versao}/abrir"
    if baixar:
        caminho += "?baixar=true"
    return quem.get(caminho, follow_redirects=False)


def test_abrir_redireciona_para_um_link_novo(logar, armazenamento):
    documento = publicar_documento(logar, armazenamento)
    resposta = _abrir(logar(COMUM), documento["id"])
    assert resposta.status_code == 302
    assert resposta.headers["location"].startswith("https://armazenamento.falso/arquivos/")
    assert resposta.headers["location"].endswith("baixar=0")
    assert resposta.headers["cache-control"] == "no-store"
    assert (
        _abrir(logar(COMUM), documento["id"], baixar=True).headers["location"].endswith("baixar=1")
    )


def test_abrir_publico_sem_sessao(cliente, logar, armazenamento):
    publico = publicar_documento(logar, armazenamento, acesso="publico")
    assert _abrir(cliente, publico["id"]).status_code == 302
    assert _abrir(cliente, publico["id"]).headers["location"].startswith("https://armazenamento")


@pytest.mark.parametrize("quem", ["sem_sessao", NAO_ATIVADA, COMUM])
def test_abrir_sem_acesso_volta_para_a_pagina_do_documento(cliente, logar, armazenamento, quem):
    # Sem acesso é igual a inexistente: a tela do Portal mostra "não achamos" (ou pede entrar).
    da_gestao = publicar_documento(logar, armazenamento, acesso="gestao")
    alvo = cliente if quem == "sem_sessao" else logar(quem)
    resposta = _abrir(alvo, da_gestao["id"])
    assert resposta.status_code == 302
    assert resposta.headers["location"] == f"/documentos/{da_gestao['id']}"
    inexistente = _abrir(alvo, 999999)
    assert inexistente.headers["location"] == "/documentos/999999"


def test_abrir_sem_bucket_volta_com_o_motivo(logar, armazenamento):
    from app.main import app
    from app.servicos.armazenamento import obter_armazenamento

    documento = publicar_documento(logar, armazenamento)
    app.dependency_overrides[obter_armazenamento] = lambda: None
    resposta = _abrir(logar(ADMIN), documento["id"])
    assert resposta.status_code == 302
    assert resposta.headers["location"] == (
        f"/documentos/{documento['id']}?erro=arquivos_desligados"
    )
