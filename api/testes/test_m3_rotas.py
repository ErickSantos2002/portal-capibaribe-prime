"""Contrato das rotas do M3 (spec do M3, seção 5): o que vale antes **e depois** dos épicos.

Sessão, permissão, CSRF, validação dos corpos, os campos novos dos avisos e o `documento` do
aviso ficam aqui e **não** são apagados pelos épicos. Os testes de 501 `em_construcao`, que os
épicos apagam, estão em `test_m3_em_construcao.py`. O envio de arquivo (pronto) está em
`test_m3_arquivos.py`.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from testes.conftest import ADMIN, CABECALHO_PORTAL, COMISSAO, COMUM, NAO_ATIVADA
from testes.test_avisos_apoio import publicar

pytestmark = pytest.mark.usefixtures("predio")

NOVO_DOCUMENTO = {
    "titulo": "Convenção do condomínio",
    "categoria": "convencao",
    "data_documento": "2026-10-01",
    "acesso": "compradores",
    "arquivo_id": 1,
}

# (método, caminho, corpo válido). `{id}` vira 1.
ROTAS_DE_GESTAO = [
    ("POST", "/api/documentos", NOVO_DOCUMENTO),
    ("POST", "/api/documentos/{id}/versoes", {"arquivo_id": 1}),
    ("POST", "/api/documentos/{id}/arquivar", None),
]
ROTAS_DE_LEITURA = [
    ("GET", "/api/documentos", None),
    ("GET", "/api/documentos/{id}", None),
]
# Sem sessão: a lista dos públicos (tela de entrada) e o link (o documento público abre).
ROTAS_PUBLICAS = [
    ("GET", "/api/documentos/publicos", None),
    ("GET", "/api/documentos/{id}/versoes/{id}/link", None),
]
ENVIO = [
    ("POST", "/api/arquivos", None),
    ("POST", "/api/arquivos/{id}/confirmar", None),
]
ANEXO = ("GET", "/api/avisos/{aviso_id}/anexos/{arquivo_id}/link")


def _url(caminho: str) -> str:
    return caminho.replace("{id}", "1")


def _codigo(resposta) -> tuple[int, str | None]:
    return resposta.status_code, resposta.json().get("codigo")


def test_rotas_do_m3_declaradas():
    from app.main import app

    no_app = {
        (metodo.upper(), caminho)
        for caminho, operacoes in app.openapi()["paths"].items()
        if caminho.startswith(("/api/documentos", "/api/arquivos")) or "/anexos/" in caminho
        for metodo in operacoes
    }
    esperadas = {
        (m, c.replace("{id}/versoes/{id}", "{documento_id}/versoes/{versao}"))
        for m, c, _ in ROTAS_DE_GESTAO + ROTAS_DE_LEITURA + ROTAS_PUBLICAS
    }
    esperadas = {(m, c.replace("{id}", "{documento_id}")) for m, c in esperadas}
    esperadas |= {(m, c.replace("{id}", "{arquivo_id}")) for m, c, _ in ENVIO}
    esperadas.add(ANEXO)
    assert no_app == esperadas


# --- épico A · documentos ----------------------------------------------------------------------


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO)
def test_gestao_de_documentos_recusa_quem_nao_e_da_gestao(cliente, logar, metodo, caminho, corpo):
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


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_LEITURA)
def test_lista_e_documento_exigem_sessao_completa(cliente, logar, metodo, caminho, corpo):
    assert _codigo(logar(NAO_ATIVADA).request(metodo, _url(caminho))) == (
        403,
        "primeiro_acesso_pendente",
    )
    assert _codigo(cliente.request(metodo, _url(caminho))) == (401, "sem_sessao")


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_PUBLICAS)
def test_rotas_publicas_nao_pedem_sessao(cliente, logar, metodo, caminho, corpo):
    for quem in (cliente, logar(NAO_ATIVADA), logar(COMUM)):
        assert quem.request(metodo, _url(caminho)).status_code not in {401, 403}


@pytest.mark.parametrize(("metodo", "caminho", "corpo"), ROTAS_DE_GESTAO + ENVIO)
def test_alteracoes_exigem_cabecalho_portal(logar, metodo, caminho, corpo):
    admin = logar(ADMIN)
    del admin.headers["X-Portal"]
    assert _codigo(admin.request(metodo, _url(caminho), json=corpo)) == (
        403,
        "requisicao_recusada",
    )


@pytest.mark.parametrize(
    ("troca", "campo", "mensagem"),
    [
        ({"titulo": "   "}, "titulo", "Escreva o título do documento."),
        ({"titulo": "x" * 121}, "titulo", "O título pode ter até 120 letras."),
        ({"titulo": "Ata‮"}, "titulo", None),
        ({"categoria": "foto"}, "categoria", None),
        ({"acesso": "todos"}, "acesso", None),
        ({"data_documento": "1989-12-31"}, "data_documento", "Escolha uma data entre 1990 e 2100."),
        ({"data_documento": "2101-01-01"}, "data_documento", "Escolha uma data entre 1990 e 2100."),
        ({"data_documento": "01/10/2026"}, "data_documento", None),
        ({"arquivo_id": None}, "arquivo_id", None),
        (
            {"acesso": "gestao", "avisar_unidades": True},
            "avisar_unidades",
            "Só dá para avisar as unidades de documento que elas podem ver.",
        ),
        ({"sobra": 1}, "sobra", None),
    ],
)
def test_novo_documento_confere_os_campos(logar, troca, campo, mensagem):
    resposta = logar(COMISSAO).post("/api/documentos", json={**NOVO_DOCUMENTO, **troca})
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert campo in {c["campo"] for c in corpo["campos"]}
    if mensagem:
        assert corpo["mensagem"] == mensagem


@pytest.mark.parametrize("categoria", ["obra", "convencao", "regimento", "ata", "contrato"])
def test_categorias_e_avisar_documento_das_unidades_passam_da_validacao(logar, categoria):
    corpo = {**NOVO_DOCUMENTO, "categoria": categoria, "acesso": "publico", "avisar_unidades": True}
    # Depois do épico A, o arquivo 1 (que não existe) dá outro erro; nunca o de validação.
    assert logar(COMISSAO).post("/api/documentos", json=corpo).json()["codigo"] != (
        "dados_invalidos"
    )


def test_nova_versao_confere_o_corpo(logar):
    resposta = logar(COMISSAO).post("/api/documentos/1/versoes", json={})
    assert _codigo(resposta) == (422, "dados_invalidos")


# --- épico B · anexos nos avisos ---------------------------------------------------------------


def test_link_do_anexo_exige_sessao_completa(cliente, logar):
    caminho = "/api/avisos/1/anexos/1/link"
    assert _codigo(logar(NAO_ATIVADA).get(caminho)) == (403, "primeiro_acesso_pendente")
    assert _codigo(cliente.get(caminho)) == (401, "sem_sessao")


def test_aviso_sem_anexos_continua_igual_ao_m1(logar):
    admin = logar(ADMIN)
    aviso = publicar(admin)
    assert aviso["anexos"] == []
    assert aviso["quantidade_anexos"] == 0
    assert aviso["documento"] is None
    explicito = admin.post(
        "/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": True, "anexos": []}
    )
    assert explicito.status_code == 201
    corrigido = admin.put(
        f"/api/avisos/{aviso['id']}", json={"titulo": "Outro", "texto": "Outro", "anexos": []}
    )
    assert corrigido.status_code == 200
    assert corrigido.json()["versoes_anteriores"][0]["anexos"] == []
    lista = logar(COMUM).get("/api/avisos").json()["itens"]
    assert {i["quantidade_anexos"] for i in lista} == {0}


@pytest.mark.parametrize("anexos", [["a"], "1", [1.5]])
def test_anexos_sao_ids(logar, anexos):
    resposta = logar(ADMIN).post(
        "/api/avisos", json={"titulo": "T", "texto": "X", "para_todos": True, "anexos": anexos}
    )
    assert _codigo(resposta) == (422, "dados_invalidos")


# --- o documento que gerou o aviso (RF-33): pronto no contrato ---------------------------------


def _documento_do_aviso(engine, predio, aviso_id: int, acesso: str = "compradores") -> int:
    with engine.begin() as con:
        arquivo = con.execute(
            text(
                "insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes,"
                " enviado_por) values (:c, 'Convenção.pdf', 'application/pdf', 'documento',"
                " 10, :u) returning id"
            ),
            {"c": f"{aviso_id:032x}", "u": predio[COMISSAO]},
        ).scalar_one()
        con.execute(text("update arquivo set confirmado_em = now() where id = :a"), {"a": arquivo})
        documento = con.execute(
            text(
                "insert into documento (titulo, categoria, data_documento, acesso, criado_por,"
                " aviso_id) values ('Convenção do condomínio', 'convencao', '2026-10-01', :ac,"
                " :u, :av) returning id"
            ),
            {"ac": acesso, "u": predio[COMISSAO], "av": aviso_id},
        ).scalar_one()
        con.execute(
            text(
                "insert into documento_versao (documento_id, versao, arquivo_id, enviada_por)"
                " values (:d, 1, :a, :u)"
            ),
            {"d": documento, "a": arquivo, "u": predio[COMISSAO]},
        )
    return documento


def test_aviso_automatico_aponta_para_o_documento(logar, engine_app, predio):
    aviso = publicar(logar(COMISSAO), titulo="Documento novo: Convenção do condomínio")
    documento = _documento_do_aviso(engine_app, predio, aviso["id"])
    for login in (COMUM, COMISSAO):
        aberto = logar(login).get(f"/api/avisos/{aviso['id']}").json()
        assert aberto["documento"] == {"id": documento, "titulo": "Convenção do condomínio"}


def test_documento_arquivado_some_do_aviso(logar, engine_app, predio):
    aviso = publicar(logar(COMISSAO))
    documento = _documento_do_aviso(engine_app, predio, aviso["id"], acesso="publico")
    with engine_app.begin() as con:
        con.execute(
            text("update documento set arquivado_em = now() where id = :d"), {"d": documento}
        )
    assert logar(COMUM).get(f"/api/avisos/{aviso['id']}").json()["documento"] is None


def test_gravar_publicacao_nao_faz_commit(engine_app, predio):
    from app.esquemas.avisos import NovoAviso
    from app.modelos import Papel
    from app.seguranca.dependencias import Logado
    from app.servicos.avisos import gravar_publicacao

    logado = Logado(
        sessao_id=0,
        unidade_id=predio[COMISSAO],
        login=COMISSAO,
        bloco=2,
        apartamento="304",
        papeis=frozenset({Papel.comissao}),
        precisa_trocar_senha=False,
    )
    with Session(engine_app) as db:
        aviso_id = gravar_publicacao(
            db, logado, NovoAviso(titulo="Documento novo", texto="Veja", para_todos=True)
        )
        assert aviso_id > 0
        db.rollback()
    with engine_app.connect() as con:
        assert con.execute(text("select count(*) from aviso")).scalar_one() == 0
