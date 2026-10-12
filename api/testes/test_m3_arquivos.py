"""Envio de arquivo (spec do M3, seções 4 e 5.1): pronto desde o contrato, comum aos épicos.

O navegador pede a URL, manda o arquivo direto ao bucket e pede para confirmar; o servidor
confere o tamanho de verdade e a assinatura do conteúdo. Um `.exe` renomeado para `.pdf` é
recusado e apagado (critério do roadmap, M3). O bucket é o falso (fixture `armazenamento`).
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.esquemas.arquivos import MSG_TIPO
from app.servicos.arquivos import arquivo_utilizavel, link_do_arquivo, tipo_pelo_conteudo
from app.servicos.visibilidade import niveis_que_ve
from testes.conftest import ADMIN, COMISSAO, COMUM, NAO_ATIVADA

pytestmark = pytest.mark.usefixtures("predio")

MB = 1024 * 1024
PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 200
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"0" * 200
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"0" * 200
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"0" * 200
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + b"0" * 200


def _pedir(cliente, **troca):
    corpo = {
        "nome": "Regras da obra.pdf",
        "tipo": "application/pdf",
        "finalidade": "documento",
        "tamanho_bytes": len(PDF),
        **troca,
    }
    return cliente.post("/api/arquivos", json=corpo)


def _pedido(cliente, **troca) -> dict:
    resposta = _pedir(cliente, **troca)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _chave(envio: dict) -> str:
    return envio["url"].split("/envios/")[1].split("?")[0]


def _linha(engine, arquivo_id: int):
    with engine.connect() as con:
        return con.execute(
            text("select tipo, tamanho_bytes, confirmado_em from arquivo where id = :a"),
            {"a": arquivo_id},
        ).one_or_none()


def _recusas(engine) -> list[dict]:
    with engine.connect() as con:
        return [
            {"unidade_id": u, "entidade": e, "detalhes": d}
            for u, e, d in con.execute(
                text(
                    "select unidade_id, entidade, detalhes from historico"
                    " where acao = 'arquivo_recusado' order by id"
                )
            )
        ]


# --- assinatura do conteúdo --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("inicio", "tipo"),
    [
        (PDF, "application/pdf"),
        (JPEG, "image/jpeg"),
        (b"\xff\xd8\xff\xdb" + b"0" * 12, "image/jpeg"),
        (PNG, "image/png"),
        (WEBP, "image/webp"),
    ],
)
def test_assinatura_dos_tipos_aceitos(inicio, tipo):
    assert tipo_pelo_conteudo(inicio[:16]) == tipo


@pytest.mark.parametrize(
    "inicio",
    [
        EXE,
        b"PK\x03\x04" + b"0" * 12,  # zip, docx
        b"<!DOCTYPE html><html>",
        b"<svg xmlns='http://www.w3.org/2000/svg'>",
        b"GIF89a" + b"0" * 10,
        b"RIFF\x24\x00\x00\x00WAVEfmt ",  # RIFF que não é WEBP
        b"  %PDF-1.7",
        b"",
        b"%PD",
        b"\xff\xd8",
    ],
)
def test_qualquer_outra_coisa_e_recusada(inicio):
    assert tipo_pelo_conteudo(inicio[:16]) is None


# --- pedir -------------------------------------------------------------------------------------


def test_pedir_cria_pendente_e_devolve_o_put(logar, armazenamento, engine_app):
    envio = _pedido(logar(COMISSAO), tipo="image/webp", nome="foto.webp", finalidade="aviso")
    assert envio["content_type"] == "image/webp"
    assert envio["url"].startswith("https://armazenamento.falso/envios/")
    assert len(_chave(envio)) == 32
    expira = datetime.fromisoformat(envio["expira_em"])
    assert abs(expira - (datetime.now(UTC) + timedelta(minutes=10))) < timedelta(seconds=10)
    tipo, tamanho, confirmado = _linha(engine_app, envio["arquivo_id"])
    assert (tipo, tamanho, confirmado) == ("image/webp", len(PDF), None)


def test_a_url_de_envio_so_aceita_o_tamanho_declarado(logar, armazenamento):
    envio = _pedido(logar(ADMIN), tamanho_bytes=len(PDF))
    assert armazenamento.tamanho_assinado[_chave(envio)] == len(PDF)


def test_cada_pedido_ganha_uma_chave_nova(logar, armazenamento):
    admin = logar(ADMIN)
    chaves = {_chave(_pedido(admin)) for _ in range(5)}
    assert len(chaves) == 5


def test_sem_bucket_configurado_503_e_nada_gravado(logar, engine_app):
    resposta = _pedir(logar(ADMIN))
    assert resposta.status_code == 503
    assert resposta.json() == {
        "codigo": "arquivos_desligados",
        "mensagem": "O envio de arquivos ainda não está ligado no Portal.",
    }
    with engine_app.connect() as con:
        assert con.execute(text("select count(*) from arquivo")).scalar_one() == 0


@pytest.mark.parametrize(
    ("troca", "campo", "mensagem"),
    [
        ({"tipo": "application/x-msdownload"}, "tipo", MSG_TIPO),
        ({"tipo": "image/svg+xml"}, "tipo", MSG_TIPO),
        (
            {"finalidade": "aviso", "tamanho_bytes": 10 * MB + 1},
            "tamanho_bytes",
            "O arquivo pode ter até 10 MB.",
        ),
        ({"tamanho_bytes": 20 * MB + 1}, "tamanho_bytes", "O arquivo pode ter até 20 MB."),
        ({"tamanho_bytes": 0}, "tamanho_bytes", None),
        ({"nome": "pasta/a.pdf"}, "nome", "O nome do arquivo não pode ter barra."),
        ({"nome": "   "}, "nome", "O arquivo precisa ter um nome."),
        ({"nome": "x" * 201}, "nome", "O nome do arquivo pode ter até 200 letras."),
        ({"nome": "fdp.‮exe"}, "nome", None),
        ({"finalidade": "foto"}, "finalidade", None),
    ],
)
def test_pedir_confere_tipo_tamanho_e_nome(logar, armazenamento, troca, campo, mensagem):
    resposta = _pedir(logar(ADMIN), **troca)
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert corpo["campos"][0]["campo"] == campo
    if mensagem:
        assert corpo["mensagem"] == mensagem


def test_limites_exatos_valem(logar, armazenamento):
    admin = logar(ADMIN)
    _pedido(admin, finalidade="aviso", tamanho_bytes=10 * MB)
    _pedido(admin, finalidade="documento", tamanho_bytes=20 * MB)


def test_pedir_e_so_da_gestao(logar, cliente, armazenamento):
    assert _pedir(logar(COMUM)).json()["codigo"] == "sem_permissao"
    assert _pedir(logar(NAO_ATIVADA)).json()["codigo"] == "primeiro_acesso_pendente"
    cliente.headers["X-Portal"] = "1"
    assert _pedir(cliente).status_code == 401
    sem_cabecalho = logar(ADMIN)
    del sem_cabecalho.headers["X-Portal"]
    assert _pedir(sem_cabecalho).json()["codigo"] == "requisicao_recusada"


def test_ate_50_por_dia(logar, armazenamento, engine_app, predio):
    with engine_app.begin() as con:
        for n in range(50):
            con.execute(
                text(
                    "insert into arquivo (chave, nome_original, tipo, finalidade,"
                    " tamanho_bytes, enviado_por) values (:c, 'a.pdf', 'application/pdf',"
                    " 'documento', 1, :u)"
                ),
                {"c": f"{n:032x}", "u": predio[ADMIN]},
            )
    resposta = _pedir(logar(ADMIN))
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "muitos_arquivos"
    # A conta é por unidade: a Comissão continua enviando.
    assert _pedir(logar(COMISSAO)).status_code == 201


def test_pendente_velho_sai_no_pedido_seguinte(
    logar, armazenamento, engine_app, engine_superusuario
):
    admin = logar(ADMIN)
    velho = _pedido(admin)["arquivo_id"]
    with engine_superusuario.begin() as con:
        con.execute(text("set local session_replication_role = replica"))
        con.execute(
            text("update arquivo set enviado_em = now() - interval '25 hours' where id = :a"),
            {"a": velho},
        )
    _pedido(admin)
    assert _linha(engine_app, velho) is None


# --- confirmar ---------------------------------------------------------------------------------


def _confirmar(cliente, arquivo_id: int):
    return cliente.post(f"/api/arquivos/{arquivo_id}/confirmar")


def test_confirmar_publica_com_o_tamanho_de_verdade(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    envio = _pedido(admin)
    chave = _chave(envio)
    armazenamento.receber(chave, PDF, "application/pdf")
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.status_code == 200, resposta.text
    assert resposta.json() == {
        "id": envio["arquivo_id"],
        "nome": "Regras da obra.pdf",
        "tipo": "application/pdf",
        "tamanho_bytes": len(PDF),
    }
    assert armazenamento.objetos == {f"arquivos/{chave}": (PDF, "application/pdf")}
    tipo, tamanho, confirmado = _linha(engine_app, envio["arquivo_id"])
    assert (tipo, tamanho) == ("application/pdf", len(PDF))
    assert confirmado is not None


def test_exe_renomeado_para_pdf_e_recusado_e_apagado(logar, armazenamento, engine_app, predio):
    admin = logar(ADMIN)
    envio = _pedido(admin, nome="Boleto de Fulano.pdf", tamanho_bytes=len(EXE))
    armazenamento.receber(_chave(envio), EXE, "application/pdf")
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "arquivo_recusado",
        "mensagem": "Este arquivo não é um PDF nem uma foto (JPEG, PNG ou WEBP). Escolha outro.",
    }
    # Some do bucket (nada em envios/ nem em arquivos/) e do banco.
    assert armazenamento.objetos == {}
    assert _linha(engine_app, envio["arquivo_id"]) is None
    [recusa] = _recusas(engine_app)
    assert recusa["unidade_id"] == predio[ADMIN]
    assert recusa["entidade"] == "arquivo"
    assert recusa["detalhes"] == {
        "motivo": "conteudo",
        "finalidade": "documento",
        "tipo_declarado": "application/pdf",
        "tipo_encontrado": None,
        "tamanho_bytes": len(EXE),
    }
    # O nome do arquivo (que pode ter nome de gente) não vai para o histórico.
    assert "Fulano" not in json.dumps(recusa)


@pytest.mark.parametrize("conteudo", [b"", b"%PD", b"<html><script>"])
def test_conteudo_vazio_curto_ou_html_tambem_e_recusado(logar, armazenamento, conteudo):
    admin = logar(ADMIN)
    envio = _pedido(admin, tamanho_bytes=max(1, len(conteudo)))
    # O vazio não passa pela URL assinada (o tamanho declarado é pelo menos 1): só por fora.
    armazenamento.gravar_por_fora(_chave(envio), conteudo)
    assert _confirmar(admin, envio["arquivo_id"]).json()["codigo"] == "arquivo_recusado"
    assert armazenamento.objetos == {}


def test_maior_que_o_limite_de_verdade_e_recusado(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    # Declarou 1 KB e o bucket tem 10 MB + 1. A URL assinada já não aceita outro tamanho, mas a
    # confirmação confere de novo: o objeto pode ter chegado por fora dela.
    envio = _pedido(admin, finalidade="aviso", tamanho_bytes=1024)
    armazenamento.gravar_por_fora(_chave(envio), PDF + b"0" * (10 * MB + 1 - len(PDF)))
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.status_code == 422
    assert resposta.json() == {
        "codigo": "arquivo_recusado",
        "mensagem": "O arquivo pode ter até 10 MB.",
    }
    assert armazenamento.objetos == {}
    assert _recusas(engine_app)[0]["detalhes"]["motivo"] == "tamanho"


def test_foto_png_com_nome_de_jpeg_vale_como_png(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    envio = _pedido(
        admin, nome="foto.jpg", tipo="image/jpeg", finalidade="aviso", tamanho_bytes=len(PNG)
    )
    chave = _chave(envio)
    armazenamento.receber(chave, PNG, "image/jpeg")
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.json()["tipo"] == "image/png"
    assert armazenamento.objetos[f"arquivos/{chave}"] == (PNG, "image/png")
    assert _linha(engine_app, envio["arquivo_id"])[0] == "image/png"


@pytest.mark.parametrize("conteudo", [JPEG, PNG, WEBP])
def test_fotos_aceitas(logar, armazenamento, conteudo):
    admin = logar(ADMIN)
    envio = _pedido(
        admin, nome="foto", tipo="image/jpeg", finalidade="aviso", tamanho_bytes=len(conteudo)
    )
    armazenamento.receber(_chave(envio), conteudo)
    assert _confirmar(admin, envio["arquivo_id"]).status_code == 200


def test_arquivo_que_nao_chegou_continua_pendente(logar, armazenamento, engine_app):
    admin = logar(ADMIN)
    envio = _pedido(admin)
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "arquivo_nao_chegou",
        "mensagem": "O arquivo não chegou ao Portal. Confira a internet e envie de novo.",
    }
    assert _linha(engine_app, envio["arquivo_id"])[2] is None
    # Chegou depois: confirma.
    armazenamento.receber(_chave(envio), PDF)
    assert _confirmar(admin, envio["arquivo_id"]).status_code == 200


def test_so_quem_pediu_confirma(logar, armazenamento):
    envio = _pedido(logar(COMISSAO))
    armazenamento.receber(_chave(envio), PDF)
    admin = logar(ADMIN)
    resposta = _confirmar(admin, envio["arquivo_id"])
    assert resposta.status_code == 404
    assert resposta.json() == _confirmar(admin, 999_999).json()
    assert resposta.json()["codigo"] == "arquivo_nao_encontrado"
    # Continua no envio, esperando quem pediu.
    assert _confirmar(logar(COMISSAO), envio["arquivo_id"]).status_code == 200


def test_confirmar_de_novo_devolve_o_mesmo(logar, armazenamento):
    admin = logar(ADMIN)
    envio = _pedido(admin)
    armazenamento.receber(_chave(envio), PDF)
    primeiro = _confirmar(admin, envio["arquivo_id"])
    segundo = _confirmar(admin, envio["arquivo_id"])
    assert segundo.status_code == 200
    assert segundo.json() == primeiro.json()


def test_confirmar_e_so_da_gestao(logar, armazenamento):
    envio = _pedido(logar(ADMIN))
    assert _confirmar(logar(COMUM), envio["arquivo_id"]).json()["codigo"] == "sem_permissao"


def test_confirmar_sem_bucket_configurado_503(logar, engine_app, predio):
    with engine_app.begin() as con:
        arquivo = con.execute(
            text(
                "insert into arquivo (chave, nome_original, tipo, finalidade, tamanho_bytes,"
                " enviado_por) values (:c, 'a.pdf', 'application/pdf', 'documento', 1, :u)"
                " returning id"
            ),
            {"c": "a" * 32, "u": predio[ADMIN]},
        ).scalar_one()
    assert _confirmar(logar(ADMIN), arquivo).json()["codigo"] == "arquivos_desligados"


# --- peças para os épicos ----------------------------------------------------------------------


def _confirmado(logar, armazenamento, login: str = ADMIN, **troca) -> int:
    cliente = logar(login)
    envio = _pedido(cliente, **troca)
    armazenamento.receber(_chave(envio), PDF)
    assert _confirmar(cliente, envio["arquivo_id"]).status_code == 200
    return envio["arquivo_id"]


def _logado(engine_app, login: str):
    from app.modelos import Papel
    from app.seguranca.dependencias import Logado

    with engine_app.connect() as con:
        unidade_id = con.execute(
            text("select id from unidade where login = :l"), {"l": login}
        ).scalar_one()
    papeis = {ADMIN: {Papel.admin}, COMISSAO: {Papel.comissao}}.get(login, set())
    return Logado(
        sessao_id=0,
        unidade_id=unidade_id,
        login=login,
        bloco=int(login[0]),
        apartamento=login[1:],
        papeis=frozenset(papeis),
        precisa_trocar_senha=login == NAO_ATIVADA,
    )


def test_arquivo_utilizavel(logar, armazenamento, engine_app):
    documento = _confirmado(logar, armazenamento)
    de_aviso = _confirmado(logar, armazenamento, finalidade="aviso")
    pendente = _pedido(logar(ADMIN))["arquivo_id"]
    da_comissao = _confirmado(logar, armazenamento, COMISSAO)
    admin = _logado(engine_app, ADMIN)
    with Session(engine_app) as db:
        assert arquivo_utilizavel(db, admin, documento, "documento").id == documento
        assert arquivo_utilizavel(db, admin, de_aviso, "documento") is None
        assert arquivo_utilizavel(db, admin, pendente, "documento") is None
        assert arquivo_utilizavel(db, admin, da_comissao, "documento") is None
        assert arquivo_utilizavel(db, admin, 999_999, "documento") is None


def test_link_do_arquivo(logar, armazenamento, engine_app):
    from app.erros_api import ErroApi
    from app.modelos import Arquivo

    arquivo_id = _confirmado(logar, armazenamento)
    with Session(engine_app) as db:
        arquivo = db.get_one(Arquivo, arquivo_id)
        link = link_do_arquivo(armazenamento, arquivo, baixar=True)
        assert link.url.startswith(f"https://armazenamento.falso/arquivos/{arquivo.chave}")
        assert "baixar=1" in link.url
        with pytest.raises(ErroApi) as erro:
            link_do_arquivo(None, arquivo, baixar=False)
    assert erro.value.status == 503


def test_niveis_que_cada_um_ve(engine_app):
    assert niveis_que_ve(None) == ("publico",)
    assert niveis_que_ve(_logado(engine_app, NAO_ATIVADA)) == ("publico",)
    assert niveis_que_ve(_logado(engine_app, COMUM)) == ("publico", "compradores")
    assert niveis_que_ve(_logado(engine_app, COMISSAO)) == ("publico", "compradores", "gestao")
    assert niveis_que_ve(_logado(engine_app, ADMIN)) == ("publico", "compradores", "gestao")
