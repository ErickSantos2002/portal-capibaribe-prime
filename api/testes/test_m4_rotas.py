"""Contrato das rotas do M4 (spec do M4, seção 3): o que vale antes **e depois** dos épicos.

Sessão, permissão, CSRF, validação dos corpos, o `enquete` do aviso aberto e o
`gravar_correcao` ficam aqui. Os 501 `em_construcao` da onda do contrato sumiram com os épicos (o
arquivo deles foi apagado no merge).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from testes.conftest import ADMIN, CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_avisos_apoio import publicar

pytestmark = pytest.mark.usefixtures("predio")

NOVA_ENQUETE = {
    "pergunta": "Qual o melhor dia para a reunião com a construtora?",
    "opcoes": ["Terça à noite", "Quinta à noite", "Sábado de manhã"],
    "encerra_em": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
    "para_todos": True,
}
EDITAR_ENQUETE = {k: v for k, v in NOVA_ENQUETE.items() if k != "para_todos"}

# (método, caminho, corpo válido). `{id}` vira 1.
ROTAS_DE_GESTAO = [
    ("POST", "/api/enquetes", NOVA_ENQUETE),
    ("PUT", "/api/enquetes/{id}", EDITAR_ENQUETE),
    ("GET", "/api/enquetes/{id}/votantes", None),
]
ROTAS_DA_UNIDADE = [
    ("GET", "/api/enquetes", None),
    ("GET", "/api/enquetes/{id}", None),
    ("PUT", "/api/enquetes/{id}/voto", {"opcoes": [1]}),
]
ALTERACOES = [r for r in ROTAS_DE_GESTAO + ROTAS_DA_UNIDADE if r[0] != "GET"]


def _url(caminho: str) -> str:
    return caminho.replace("{id}", "1")


def _codigo(resposta) -> tuple[int, str | None]:
    return resposta.status_code, resposta.json().get("codigo")


def test_rotas_do_m4_declaradas():
    from app.main import app

    no_app = {
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith("/api/enquetes")
        for metodo in operacoes
    }
    esperadas = {
        (m, c.replace("{id}", "{enquete_id}")) for m, c, _ in ROTAS_DE_GESTAO + ROTAS_DA_UNIDADE
    }
    assert no_app == esperadas


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO)
def test_gestao_recusa_quem_nao_e_da_gestao(cliente, logar, metodo, caminho, corpo):
    assert _codigo(logar(COMUM).request(metodo, _url(caminho), json=corpo)) == (
        403,
        "sem_permissao",
    )
    assert _codigo(logar(NAO_ATIVADA).request(metodo, _url(caminho), json=corpo)) == (
        403,
        "primeiro_acesso_pendente",
    )
    cliente.headers.update(CABECALHO_PORTAL)
    assert _codigo(cliente.request(metodo, _url(caminho), json=corpo)) == (401, "sem_sessao")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DA_UNIDADE)
def test_lista_enquete_e_voto_exigem_sessao_completa(cliente, logar, metodo, caminho, corpo):
    assert _codigo(logar(NAO_ATIVADA).request(metodo, _url(caminho), json=corpo)) == (
        403,
        "primeiro_acesso_pendente",
    )
    cliente.headers.update(CABECALHO_PORTAL)
    assert _codigo(cliente.request(metodo, _url(caminho), json=corpo)) == (401, "sem_sessao")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ALTERACOES)
def test_alteracoes_exigem_cabecalho_portal(logar, metodo, caminho, corpo):
    admin = logar(ADMIN)
    del admin.headers["X-Portal"]
    assert _codigo(admin.request(metodo, _url(caminho), json=corpo)) == (
        403,
        "requisicao_recusada",
    )


@pytest.mark.parametrize(
    "caminho", ["/api/enquetes/0", "/api/enquetes/9223372036854775808", "/api/enquetes/x"]
)
def test_id_fora_do_bigint_e_422(logar, caminho):
    comum = logar(COMUM)
    assert _codigo(comum.get(caminho)) == (422, "dados_invalidos")
    assert _codigo(comum.put(f"{caminho}/voto", json={"opcoes": [1]})) == (422, "dados_invalidos")


@pytest.mark.parametrize(
    ("troca", "campo", "mensagem"),
    [
        ({"pergunta": "  "}, "pergunta", "Escreva a pergunta."),
        ({"opcoes": ["Sim"]}, "opcoes", "Escreva pelo menos 2 opções de resposta."),
        ({"opcoes": ["Sim", "sim"]}, "opcoes", "Duas opções estão iguais."),
        ({"encerra_em": "2020-01-01T20:00:00-03:00"}, "encerra_em", None),
        ({"mostrar_resultado": "nunca"}, "mostrar_resultado", None),
        ({"para_todos": False}, "blocos", "Escolha pelo menos um bloco, ou Todos os blocos."),
        ({"sobra": 1}, "sobra", None),
    ],
)
def test_nova_enquete_confere_os_campos(logar, troca, campo, mensagem):
    resposta = logar(COMISSAO).post("/api/enquetes", json={**NOVA_ENQUETE, **troca})
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert campo in {c["campo"] for c in corpo["campos"]}
    if mensagem:
        assert corpo["mensagem"] == mensagem


def test_editar_nao_aceita_destino(logar):
    resposta = logar(COMISSAO).put("/api/enquetes/1", json={**EDITAR_ENQUETE, "para_todos": True})
    assert _codigo(resposta) == (422, "dados_invalidos")


@pytest.mark.parametrize("corpo", [{}, {"opcoes": []}, {"opcoes": [1, 1]}, {"opcoes": ["a"]}])
def test_votar_confere_o_corpo(logar, corpo):
    assert _codigo(logar(COMUM).put("/api/enquetes/1/voto", json=corpo)) == (
        422,
        "dados_invalidos",
    )


# --- a enquete que gerou o aviso (H-13): pronto no contrato -------------------------------------


def _enquete_do_aviso(engine, predio, aviso_id: int, pergunta: str = "Qual o melhor dia?") -> int:
    with engine.begin() as con:
        enquete = con.execute(
            text(
                "insert into enquete (pergunta, encerra_em, para_todos, criada_por, aviso_id)"
                " values (:p, now() + interval '7 days', true, :u, :a) returning id"
            ),
            {"p": pergunta, "u": predio[COMISSAO], "a": aviso_id},
        ).scalar_one()
        for ordem, opcao in enumerate(("Terça", "Quinta"), start=1):
            con.execute(
                text("insert into enquete_opcao (enquete_id, texto, ordem) values (:e, :t, :o)"),
                {"e": enquete, "t": opcao, "o": ordem},
            )
    return enquete


def test_aviso_comum_nao_tem_enquete(logar):
    assert publicar(logar(ADMIN))["enquete"] is None


def test_aviso_automatico_aponta_para_a_enquete(logar, engine_app, predio):
    aviso = publicar(logar(COMISSAO), titulo="Enquete nova: Qual o melhor dia?")
    enquete = _enquete_do_aviso(engine_app, predio, aviso["id"])
    for login in (COMUM, COMISSAO):
        aberto = logar(login).get(f"/api/avisos/{aviso['id']}").json()
        assert aberto["enquete"] == {"id": enquete, "pergunta": "Qual o melhor dia?"}
    # A pergunta é a atual: editada antes do 1º voto, o botão acompanha.
    with engine_app.begin() as con:
        con.execute(
            text("update enquete set pergunta = 'Qual o melhor horário?' where id = :e"),
            {"e": enquete},
        )
    aberto = logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()
    assert aberto["enquete"]["pergunta"] == "Qual o melhor horário?"


def test_botao_da_enquete_so_para_quem_esta_no_destino(logar, engine_app, engine_superusuario):
    """Revisão do contrato, achado 6: o banco não deixa o aviso ter outro destino; se mesmo assim
    acontecer (correção à mão), o aviso não mostra a pergunta a quem não vê a enquete."""
    aviso = publicar(logar(COMISSAO), para_todos=False, blocos=[2])
    with engine_app.begin() as con:
        enquete = con.execute(
            text(
                "insert into enquete (pergunta, encerra_em, para_todos, criada_por, aviso_id)"
                " select 'Só do Bloco 2?', now() + interval '7 days', false, publicado_por, id"
                " from aviso where id = :a returning id"
            ),
            {"a": aviso["id"]},
        ).scalar_one()
        for ordem, opcao in enumerate(("Sim", "Não"), start=1):
            con.execute(
                text("insert into enquete_opcao (enquete_id, texto, ordem) values (:e, :t, :o)"),
                {"e": enquete, "t": opcao, "o": ordem},
            )
        con.execute(
            text(
                "insert into enquete_bloco (enquete_id, bloco_id)"
                " select :e, id from bloco where numero = 2"
            ),
            {"e": enquete},
        )
    # À mão, sem as triggers: o aviso passa a ir também para o Bloco 1.
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text(
                "insert into aviso_bloco (aviso_id, bloco_id)"
                " select :a, id from bloco where numero = 1"
            ),
            {"a": aviso["id"]},
        )
    assert logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()["enquete"] is None
    assert logar(COMISSAO).get(f"/api/avisos/{aviso['id']}").json()["enquete"]["id"] == enquete


def _logado(predio):
    from app.modelos import Papel
    from app.seguranca.dependencias import Logado

    return Logado(
        sessao_id=0,
        unidade_id=predio[COMISSAO],
        login=COMISSAO,
        bloco=2,
        apartamento="304",
        papeis=frozenset({Papel.comissao}),
        precisa_trocar_senha=False,
    )


def test_gravar_correcao_nao_faz_commit(logar, engine_app, predio):
    from app.esquemas.avisos import CorrigirAviso
    from app.servicos.avisos import gravar_correcao

    aviso = publicar(logar(COMISSAO))
    with Session(engine_app) as db:
        versao = gravar_correcao(
            db, _logado(predio), aviso["id"], CorrigirAviso(titulo="Outro", texto="Outro")
        )
        assert versao == 2
        db.rollback()
    with engine_app.connect() as con:
        assert con.execute(text("select max(versao) from aviso_versao")).scalar_one() == 1


def test_corrigir_continua_fazendo_commit(logar):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    corrigido = comissao.put(f"/api/avisos/{aviso['id']}", json={"titulo": "Novo", "texto": "X"})
    assert corrigido.status_code == 200
    assert comissao.get(f"/api/avisos/{aviso['id']}").json()["titulo"] == "Novo"
