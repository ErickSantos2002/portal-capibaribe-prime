"""NUL e caracteres de controle em texto livre: 422 em português, nunca 500 (revisão do M1, C3).

O Postgres recusa `\\x00` em `text` (o psycopg levanta antes de gravar) e isso virava erro 500.
Os outros caracteres de controle (C0, DEL, C1) não têm uso em nome, e-mail, título ou busca;
no texto do aviso, só a quebra de linha e a tabulação valem.
"""

import pytest

from app.esquemas.comum import MSG_CONTROLE
from testes.conftest import ADMIN, COMUM, NAO_ATIVADA
from testes.test_avisos_apoio import publicar

pytestmark = pytest.mark.usefixtures("predio")

CONTATO = {"responsavel_nome": "Maria", "celular": "81912345678", "email": None}
PROIBIDOS = ["\x00", "\x07", "\x1b", "\x7f", "\x85", "\r"]


def _confere_422(resposta, campo: str) -> None:
    assert resposta.status_code == 422, resposta.text
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert {"campo": campo, "mensagem": MSG_CONTROLE} in corpo["campos"]


@pytest.mark.parametrize("ruim", PROIBIDOS)
@pytest.mark.parametrize("campo", ["responsavel_nome", "celular", "email"])
def test_contato_com_controle(logar, campo, ruim):
    corpo = {**CONTATO, "email": "maria@example.com", campo: f"ab{ruim}c"}
    if campo == "celular":
        corpo[campo] = f"8191234{ruim}5678"
    _confere_422(logar(COMUM).put("/api/minha-unidade/dados", json=corpo), campo)


def test_primeiro_acesso_com_nul(logar):
    corpo = {
        **CONTATO,
        "responsavel_nome": "Ma\x00ria",
        "senha_nova": "senha-boa-123",
        "senha_nova_repetida": "senha-boa-123",
    }
    _confere_422(
        logar(NAO_ATIVADA).post("/api/acesso/primeiro-acesso", json=corpo), "responsavel_nome"
    )


@pytest.mark.parametrize("campo", ["senha_nova"])
def test_senha_nova_com_nul(logar, campo):
    corpo = {"senha_atual": "senha-1203", "senha_nova": "abc\x00defgh", "senha_nova_repetida": "x"}
    _confere_422(logar(COMUM).put("/api/minha-unidade/senha", json=corpo), campo)


def test_entrar_com_nul_na_senha_nao_e_500(cliente):
    resposta = cliente.post(
        "/api/acesso/entrar", json={"login": COMUM, "senha": "a\x00b"}, headers={"X-Portal": "1"}
    )
    assert resposta.status_code == 401


@pytest.mark.parametrize("ruim", PROIBIDOS[:-1])
@pytest.mark.parametrize("campo", ["titulo", "texto"])
def test_aviso_com_controle(logar, campo, ruim):
    corpo = {"titulo": "Título", "texto": "Texto", "para_todos": True, campo: f"a{ruim}b"}
    admin = logar(ADMIN)
    _confere_422(admin.post("/api/avisos", json=corpo), campo)
    aviso = publicar(admin)
    corrigir = {"titulo": "Outro", "texto": "Outro texto", campo: f"a{ruim}b"}
    _confere_422(admin.put(f"/api/avisos/{aviso['id']}", json=corrigir), campo)


def test_texto_do_aviso_aceita_quebra_e_tabulacao(logar):
    aviso = publicar(logar(ADMIN), texto="Linha 1\n\tLinha 2\r\nLinha 3")
    assert aviso["texto"] == "Linha 1\n\tLinha 2\nLinha 3"


def test_titulo_nao_aceita_quebra(logar):
    corpo = {"titulo": "Um\ndois", "texto": "Texto", "para_todos": True}
    _confere_422(logar(ADMIN).post("/api/avisos", json=corpo), "titulo")


def test_busca_com_nul(logar):
    resposta = logar(COMUM).get("/api/avisos", params={"busca": "a\x00b"})
    _confere_422(resposta, "busca")
