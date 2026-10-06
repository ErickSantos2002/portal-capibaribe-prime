"""Avisos com formatação, categoria e evento: a API (spec de 06/10/2026, seções 3.1 e 3.3)."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.esquemas.avisos import Categoria, NovoAviso
from app.servicos.avisos import resumir
from testes.test_avisos_apoio import COMISSAO, COMUM, publicar

EVENTO = {"quando": "2026-10-11T09:00:00-03:00", "onde": "Stand de vendas"}


def _publicar(cliente, **extra: Any) -> dict[str, Any]:
    corpo = {"titulo": "Vistoria", "texto": "Sábado.", "para_todos": True, **extra}
    resposta = cliente.post("/api/avisos", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# --- resumo do mural sem marcas (3.1) -----------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Olá, **vizinhos**!\n\nResto.", "Olá, vizinhos!"),
        ("## Como entrar\nCada apartamento.", "Como entrar Cada apartamento."),
        ("- um\n- dois", "um dois"),
        ("1. um\n2. dois\n10. dez", "um dois dez"),
        ("> Atenção: **prazo** sexta.", "Atenção: prazo sexta."),
        # Sem par, o asterisco é do autor e fica; marca sem espaço não é marca.
        ("Nota 5 ** de 10", "Nota 5 ** de 10"),
        ("#hashtag e -traço", "#hashtag e -traço"),
    ],
)
def test_resumir_tira_as_marcas(texto, esperado):
    assert resumir(texto) == esperado


def test_resumir_corta_depois_de_tirar_as_marcas():
    assert resumir("**" + "a" * 199 + "**") == "a" * 199
    assert resumir("**" + "a" * 250 + "**").endswith("…")


# --- esquemas -----------------------------------------------------------------------------------


def test_categorias_iguais_as_do_banco():
    from app.modelos.avisos import CATEGORIAS

    assert tuple(c.value for c in Categoria) == CATEGORIAS


def test_categoria_padrao_e_geral_e_evento_e_opcional():
    aviso = NovoAviso(titulo="T", texto="X", para_todos=True)
    assert aviso.categoria is Categoria.geral
    assert aviso.evento is None


def test_onde_vazio_vira_sem_local():
    aviso = NovoAviso.model_validate(
        {"titulo": "T", "texto": "X", "para_todos": True, "evento": {**EVENTO, "onde": "  "}}
    )
    assert aviso.evento is not None and aviso.evento.onde is None


def test_onde_sem_espacos_nas_pontas():
    aviso = NovoAviso.model_validate(
        {"titulo": "T", "texto": "X", "para_todos": True, "evento": {**EVENTO, "onde": " Stand "}}
    )
    assert aviso.evento is not None and aviso.evento.onde == "Stand"


def test_quando_sem_fuso_recusado():
    with pytest.raises(ValidationError, match="fuso"):
        NovoAviso.model_validate(
            {
                "titulo": "T",
                "texto": "X",
                "para_todos": True,
                "evento": {"quando": "2026-10-11T09:00:00"},
            }
        )


# --- API ----------------------------------------------------------------------------------------


@pytest.mark.usefixtures("predio")
class TestApi:
    def test_publica_com_categoria_e_evento(self, logar):
        aviso = _publicar(logar(COMISSAO), categoria="obra", evento=EVENTO)
        assert aviso["categoria"] == "obra"
        assert aviso["evento"] == {"quando": "2026-10-11T12:00:00Z", "onde": "Stand de vendas"}
        assert aviso["evento_quando"] == "2026-10-11T12:00:00Z"
        item = logar(COMUM).get("/api/avisos").json()["itens"][0]
        assert item["categoria"] == "obra"
        assert item["evento_quando"] == "2026-10-11T12:00:00Z"

    def test_sem_categoria_e_geral_sem_evento(self, logar):
        aviso = publicar(logar(COMISSAO))
        assert aviso["categoria"] == "geral"
        assert aviso["evento"] is None
        assert aviso["evento_quando"] is None

    def test_evento_no_passado_aceito_e_sem_local(self, logar):
        aviso = _publicar(logar(COMISSAO), evento={"quando": "2020-01-02T19:00:00-03:00"})
        assert aviso["evento"] == {"quando": "2020-01-02T22:00:00Z", "onde": None}

    @pytest.mark.parametrize("categoria", ["festa", "Obra", "", None])
    def test_categoria_invalida_422(self, logar, categoria):
        resposta = logar(COMISSAO).post(
            "/api/avisos",
            json={"titulo": "T", "texto": "X", "para_todos": True, "categoria": categoria},
        )
        assert resposta.status_code == 422
        assert resposta.json()["campos"][0]["campo"] == "categoria"

    @pytest.mark.parametrize(
        "evento",
        [
            {"onde": "Stand de vendas"},
            {"quando": None, "onde": "Stand"},
            {"quando": "amanhã"},
            {"quando": "2026-10-11T09:00:00"},
            {"quando": "2026-10-11T09:00:00-03:00", "onde": "x" * 121},
            {"quando": "2026-10-11T09:00:00-03:00", "onde": "Stand\x00"},
            {"quando": "2026-10-11T09:00:00-03:00", "extra": 1},
        ],
    )
    def test_evento_invalido_422(self, logar, evento):
        resposta = logar(COMISSAO).post(
            "/api/avisos",
            json={"titulo": "T", "texto": "X", "para_todos": True, "evento": evento},
        )
        assert resposta.status_code == 422, resposta.text

    def test_onde_sem_quando_diz_o_que_falta(self, logar):
        resposta = logar(COMISSAO).post(
            "/api/avisos",
            json={"titulo": "T", "texto": "X", "para_todos": True, "evento": {"onde": "Stand"}},
        )
        assert resposta.json()["mensagem"] == "Escolha o dia e a hora do evento."

    def test_conta_comum_nao_publica(self, logar):
        resposta = logar(COMUM).post(
            "/api/avisos",
            json={
                "titulo": "T",
                "texto": "X",
                "para_todos": True,
                "categoria": "urgente",
                "evento": EVENTO,
            },
        )
        assert resposta.status_code == 403

    def test_conta_comum_nao_corrige(self, logar):
        aviso = publicar(logar(COMISSAO))
        resposta = logar(COMUM).put(
            f"/api/avisos/{aviso['id']}",
            json={"titulo": aviso["titulo"], "texto": aviso["texto"], "categoria": "urgente"},
        )
        assert resposta.status_code == 403

    def test_correcao_muda_categoria_e_evento_e_a_antiga_guarda_os_dela(self, logar):
        comissao = logar(COMISSAO)
        aviso = _publicar(comissao, categoria="reuniao", evento=EVENTO)
        resposta = comissao.put(
            f"/api/avisos/{aviso['id']}",
            json={"titulo": "Vistoria", "texto": "Sábado.", "categoria": "urgente"},
        )
        assert resposta.status_code == 200, resposta.text
        corrigido = resposta.json()
        assert corrigido["categoria"] == "urgente"
        assert corrigido["evento"] is None
        [antiga] = corrigido["versoes_anteriores"]
        assert antiga["categoria"] == "reuniao"
        assert antiga["evento"] == {"quando": "2026-10-11T12:00:00Z", "onde": "Stand de vendas"}

    def test_correcao_so_do_evento_cria_versao(self, logar):
        comissao = logar(COMISSAO)
        aviso = _publicar(comissao, evento=EVENTO)
        outro = {"quando": "2026-10-11T10:30:00-03:00", "onde": "Stand de vendas"}
        resposta = comissao.put(
            f"/api/avisos/{aviso['id']}",
            json={"titulo": "Vistoria", "texto": "Sábado.", "evento": outro},
        )
        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["evento"]["quando"] == "2026-10-11T13:30:00Z"

    def test_correcao_igual_com_mesmo_evento_e_sem_mudanca(self, logar):
        comissao = logar(COMISSAO)
        aviso = _publicar(comissao, categoria="obra", evento=EVENTO)
        # Mesmo instante em outro fuso também é "nada mudou".
        resposta = comissao.put(
            f"/api/avisos/{aviso['id']}",
            json={
                "titulo": "Vistoria",
                "texto": "Sábado.",
                "categoria": "obra",
                "evento": {"quando": "2026-10-11T12:00:00Z", "onde": "Stand de vendas"},
            },
        )
        assert resposta.status_code == 409
        assert resposta.json()["codigo"] == "sem_mudanca"
