"""RNF-13 · Permissões dos avisos conferidas no servidor (portão do M1, issue #18).

- toda rota de gestão recusa a unidade comum e a sessão restrita do primeiro acesso;
- toda rota de leitura recusa a sessão restrita e quem não entrou;
- morador do Bloco 2 não vê nem conta aviso do Bloco 1.
"""

import pytest
from sqlalchemy import text

from testes.test_avisos_apoio import COMISSAO, COMUM, NAO_ATIVADA, ativar, publicar

pytestmark = pytest.mark.usefixtures("predio")

CORPO_NOVO = {"titulo": "T", "texto": "X", "para_todos": True}
CORPO_CORRIGIR = {"titulo": "Outro", "texto": "Outro"}

# (método, caminho, corpo). `{id}` é trocado pelo aviso publicado na fixture.
ROTAS_DE_GESTAO = [
    ("POST", "/api/avisos", CORPO_NOVO),
    ("GET", "/api/avisos/alcance", None),
    ("GET", "/api/avisos/destinos", None),
    ("PUT", "/api/avisos/{id}", CORPO_CORRIGIR),
    ("POST", "/api/avisos/{id}/arquivar", None),
    ("PUT", "/api/avisos/{id}/fixado", {"fixado": True}),
    ("GET", "/api/avisos/{id}/leitura", None),
]
ROTAS_DE_LEITURA = [
    ("GET", "/api/avisos", None),
    ("GET", "/api/avisos/nao-lidos", None),
    ("GET", "/api/avisos/{id}", None),
    ("POST", "/api/avisos/{id}/lido", None),
]


@pytest.fixture
def aviso_id(logar) -> int:
    return publicar(logar(COMISSAO))["id"]


def _pedir(cliente, metodo: str, caminho: str, corpo, aviso_id: int):
    return cliente.request(metodo, caminho.format(id=aviso_id), json=corpo)


def _contar_avisos(engine) -> tuple[int, int]:
    with engine.connect() as con:
        return (
            con.execute(text("select count(*) from aviso")).scalar_one(),
            con.execute(text("select count(*) from aviso_versao")).scalar_one(),
        )


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO)
def test_gestao_recusa_unidade_comum(logar, engine_app, aviso_id, metodo, caminho, corpo):
    antes = _contar_avisos(engine_app)
    resposta = _pedir(logar(COMUM), metodo, caminho, corpo, aviso_id)
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "sem_permissao"
    assert _contar_avisos(engine_app) == antes


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO + ROTAS_DE_LEITURA)
def test_recusa_sessao_restrita(logar, aviso_id, metodo, caminho, corpo):
    resposta = _pedir(logar(NAO_ATIVADA), metodo, caminho, corpo, aviso_id)
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "primeiro_acesso_pendente"


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO + ROTAS_DE_LEITURA)
def test_recusa_sem_sessao(cliente, aviso_id, metodo, caminho, corpo):
    cliente.headers["X-Portal"] = "1"
    resposta = _pedir(cliente, metodo, caminho, corpo, aviso_id)
    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "sem_sessao"


def test_papel_retirado_vale_na_hora(logar, engine_app, predio):
    comissao = logar(COMISSAO)
    with engine_app.begin() as con:
        con.execute(
            text("update unidade_papel set retirado_em = now() where unidade_id = :u"),
            {"u": predio[COMISSAO]},
        )
    resposta = comissao.post("/api/avisos", json=CORPO_NOVO)
    assert resposta.status_code == 403


# --- morador do Bloco 2 não vê nem conta aviso do Bloco 1 --------------------------------------


def test_bloco_2_nao_ve_aviso_do_bloco_1(logar, engine_app):
    morador_id = ativar(engine_app, "2101")
    comissao = logar(COMISSAO)
    do_bloco_1 = publicar(
        comissao, titulo="Só do Bloco 1", texto="Assunto do Bloco 1", para_todos=False, blocos=[1]
    )
    arquivado = publicar(comissao, titulo="Arquivado do Bloco 1", para_todos=False, blocos=[1])
    comissao.post(f"/api/avisos/{arquivado['id']}/arquivar")
    publicar(comissao, titulo="Para todos")

    morador = logar("2101")
    assert [i["titulo"] for i in morador.get("/api/avisos").json()["itens"]] == ["Para todos"]
    assert morador.get("/api/avisos", params={"busca": "bloco 1"}).json()["itens"] == []
    assert morador.get("/api/avisos", params={"arquivados": "true"}).json()["itens"] == []
    assert morador.get("/api/avisos/nao-lidos").json() == {"quantidade": 1}

    for caminho, metodo in [
        (f"/api/avisos/{do_bloco_1['id']}", "GET"),
        (f"/api/avisos/{do_bloco_1['id']}/lido", "POST"),
        (f"/api/avisos/{arquivado['id']}", "GET"),
    ]:
        resposta = morador.request(metodo, caminho)
        # Igual a aviso inexistente: não revela que existe.
        assert resposta.status_code == 404
        assert resposta.json() == morador.get("/api/avisos/999999").json()
    with engine_app.connect() as con:
        leituras = con.execute(
            text("select count(*) from aviso_leitura where unidade_id = :u"), {"u": morador_id}
        ).scalar_one()
    assert leituras == 0

    # E o morador do Bloco 1 vê.
    assert logar(COMUM).get(f"/api/avisos/{do_bloco_1['id']}").status_code == 200
