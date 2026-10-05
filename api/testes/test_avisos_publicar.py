"""H-12 · Publicar aviso: rota `POST /api/avisos`, prévia (`alcance`), destinos e abrir."""

import pytest
from sqlalchemy import text

from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, historico, publicar

pytestmark = pytest.mark.usefixtures("predio")


def _contar(engine, tabela: str) -> int:
    with engine.connect() as con:
        return con.execute(text(f"select count(*) from {tabela}")).scalar_one()


# --- H-12: título, texto e destino ------------------------------------------------------------


def test_publica_para_todos(logar, engine_app, predio):
    aviso = publicar(
        logar(COMISSAO), titulo="  Vistoria da obra  ", texto="Linha 1\r\nLinha 2\n\nParte 2"
    )
    assert aviso["titulo"] == "Vistoria da obra"
    assert aviso["texto"] == "Linha 1\nLinha 2\n\nParte 2"
    assert aviso["para_todos"] is True
    assert aviso["blocos"] == []
    assert aviso["fixado"] is False
    assert aviso["arquivado_em"] is None
    assert aviso["editado_em"] is None
    assert aviso["versoes_anteriores"] == []
    assert aviso["publicado_em"]
    # Quem publica já leu (como no protótipo): o aviso não aparece como "Novo" para ela.
    assert aviso["lido"] is True
    assert aviso["leitura"] == {"lidos": 1, "total": 320}

    assert historico(engine_app, "aviso_publicado") == [
        {
            "unidade_id": predio[COMISSAO],
            "entidade": "aviso",
            "entidade_id": aviso["id"],
            "detalhes": {
                "titulo": "Vistoria da obra",
                "para_todos": True,
                "blocos": [],
                "fixado": False,
            },
        }
    ]


def test_publica_para_blocos(logar, engine_app):
    aviso = publicar(logar(COMISSAO), para_todos=False, blocos=[3, 1, 3])
    assert aviso["para_todos"] is False
    assert aviso["blocos"] == [1, 3]
    # 64 unidades por bloco; quem publicou é do Bloco 2, fora do destino: não conta.
    assert aviso["leitura"] == {"lidos": 0, "total": 128}
    assert _contar(engine_app, "aviso_bloco") == 2


def test_blocos_sao_ignorados_quando_para_todos(logar):
    aviso = publicar(logar(COMISSAO), para_todos=True, blocos=[2])
    assert aviso["blocos"] == []


def test_publica_fixado(logar):
    assert publicar(logar(COMISSAO), fixado=True)["fixado"] is True


# --- H-12: "Publicado pela Comissão" e a data -------------------------------------------------


def test_assinatura_da_comissao(logar):
    assert publicar(logar(COMISSAO))["publicado_por"] == "Comissão"


def test_assinatura_do_admin(logar):
    assert publicar(logar(ADMIN))["publicado_por"] == "Administração do Portal"


def test_assinatura_prefere_comissao(logar, engine_app, predio):
    with engine_app.begin() as con:
        con.execute(
            text("insert into unidade_papel (unidade_id, papel) values (:u, 'comissao')"),
            {"u": predio[ADMIN]},
        )
    assert publicar(logar(ADMIN))["publicado_por"] == "Comissão"


def test_assinatura_fica_quando_o_papel_sai(logar, engine_app, predio):
    aviso = publicar(logar(COMISSAO))
    with engine_app.begin() as con:
        con.execute(
            text("update unidade_papel set retirado_em = now() where unidade_id = :u"),
            {"u": predio[COMISSAO]},
        )
    lido = logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()
    assert lido["publicado_por"] == "Comissão"


# --- recusas ----------------------------------------------------------------------------------


def test_bloco_inexistente(logar, engine_app):
    resposta = logar(COMISSAO).post(
        "/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": False, "blocos": [2, 9]}
    )
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "bloco_inexistente"
    assert corpo["mensagem"] == "O Bloco 9 não existe."
    assert corpo["campos"] == [{"campo": "blocos", "mensagem": "O Bloco 9 não existe."}]
    assert _contar(engine_app, "aviso") == 0


def test_bloco_inativo_nao_e_destino(logar, engine_app):
    with engine_app.begin() as con:
        con.execute(text("update bloco set ativo = false where numero = 5"))
    resposta = logar(COMISSAO).post(
        "/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": False, "blocos": [5]}
    )
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "bloco_inexistente"


@pytest.mark.parametrize(
    ("corpo", "campo", "mensagem"),
    [
        ({"titulo": " ", "texto": "X", "para_todos": True}, "titulo", "Escreva o título do aviso."),
        ({"titulo": "T", "texto": "", "para_todos": True}, "texto", "Escreva o texto do aviso."),
        (
            {"titulo": "t" * 121, "texto": "X", "para_todos": True},
            "titulo",
            "O título pode ter até 120 letras.",
        ),
        (
            {"titulo": "T", "texto": "X", "para_todos": False},
            "blocos",
            "Escolha pelo menos um bloco, ou Todos os blocos.",
        ),
    ],
)
def test_validacao(logar, engine_app, corpo, campo, mensagem):
    resposta = logar(COMISSAO).post("/api/avisos", json=corpo)
    assert resposta.status_code == 422
    assert {"campo": campo, "mensagem": mensagem} in resposta.json()["campos"]
    assert _contar(engine_app, "aviso") == 0


def test_texto_puro_volta_igual(logar):
    # A API guarda e devolve o texto como foi escrito; quem não interpreta HTML é a tela.
    texto = '<script>alert("x")</script>\n\n<b>negrito?</b> https://exemplo.com.br/a?b=1&c=2'
    aviso = publicar(logar(COMISSAO), texto=texto)
    assert logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()["texto"] == texto


def test_publicar_sem_cabecalho_portal_e_recusado(logar, engine_app):
    cliente = logar(COMISSAO)
    del cliente.headers["X-Portal"]
    resposta = cliente.post("/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": True})
    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "requisicao_recusada"
    assert _contar(engine_app, "aviso") == 0


# --- H-12: prévia com quantas unidades recebem ------------------------------------------------


def test_alcance_de_todos(logar):
    assert logar(COMISSAO).get("/api/avisos/alcance").json() == {"unidades": 320}


def test_alcance_de_blocos(logar):
    resposta = logar(COMISSAO).get("/api/avisos/alcance", params={"blocos": [1, 3]})
    assert resposta.json() == {"unidades": 128}


def test_alcance_conta_so_unidades_ativas(logar, engine_app):
    with engine_app.begin() as con:
        con.execute(text("update unidade set ativa = false where login in ('1102', '3102')"))
    assert logar(COMISSAO).get("/api/avisos/alcance").json() == {"unidades": 318}
    resposta = logar(COMISSAO).get("/api/avisos/alcance", params={"blocos": [1]})
    assert resposta.json() == {"unidades": 63}


def test_alcance_de_bloco_inexistente(logar):
    resposta = logar(COMISSAO).get("/api/avisos/alcance", params={"blocos": [1, 7]})
    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "bloco_inexistente"
    assert resposta.json()["mensagem"] == "O Bloco 7 não existe."


def test_destinos(logar, engine_app):
    with engine_app.begin() as con:
        con.execute(text("update bloco set ativo = false where numero = 5"))
    assert logar(COMISSAO).get("/api/avisos/destinos").json() == {
        "blocos": [{"numero": n, "nome": f"Bloco {n}"} for n in (1, 2, 3, 4)]
    }


# --- abrir só lê ------------------------------------------------------------------------------


def test_abrir_nao_grava_leitura(logar, engine_app):
    aviso = publicar(logar(COMISSAO))
    resposta = logar(COMUM).get(f"/api/avisos/{aviso['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["lido"] is False
    assert _contar(engine_app, "aviso_leitura") == 1  # só a de quem publicou


def test_abrir_aviso_inexistente(logar):
    resposta = logar(COMUM).get("/api/avisos/999")
    assert resposta.status_code == 404
    assert resposta.json() == {
        "codigo": "aviso_nao_encontrado",
        "mensagem": (
            "Não achamos este aviso. O link pode estar incompleto, ou ele é de outro bloco."
        ),
    }
