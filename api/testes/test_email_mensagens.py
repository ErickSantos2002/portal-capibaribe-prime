"""As duas mensagens do Portal (spec do épico B, seções 2.1 a 2.3): cópia do aviso e link de
recuperação. Só montagem: nada aqui conecta a servidor nenhum."""

import re
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import parseaddr

import pytest

from app.configuracao import ConfigEmail
from app.esquemas.comum import UnidadeRef
from app.modelos import Papel
from app.servicos.email import linha_de_publicacao, mensagem_de_recuperacao, mensagem_do_aviso
from app.servicos.notificacoes import AvisoParaNotificar

CONFIG = ConfigEmail(
    usuario="portal@example.com",
    senha_app="senha-de-app-falsa",
    host="smtp.example.com",
    porta=465,
    url_base="https://portal.example.com",
)
AVISO = AvisoParaNotificar(
    aviso_id=7,
    titulo="Falta d'água no Bloco 1",
    texto="A **água** volta às 18h.\n\n- Encha os baldes\n- Feche os registros",
    categoria="urgente",
    publicado_por=1,
    para_todos=False,
    blocos=(1,),
)
TOKEN = "Tk_" + "x" * 40
PUBLICACAO = "Publicado pela Comissão em 07/10, às 21h23"


def _partes(mensagem: EmailMessage) -> tuple[str, str]:
    texto = mensagem.get_body(("plain",))
    html = mensagem.get_body(("html",))
    assert texto is not None and html is not None
    return texto.get_content(), html.get_content()


@pytest.fixture
def aviso() -> EmailMessage:
    return mensagem_do_aviso(AVISO, "morador@example.com", CONFIG, PUBLICACAO)


def test_cabecalhos_do_aviso(aviso):
    # Revisão de UX, item 9: o assunto é o título; "Urgente: " na frente só se for urgente.
    assert aviso["Subject"] == "Urgente: Falta d'água no Bloco 1"
    assert parseaddr(aviso["From"]) == ("Portal Capibaribe Prime", "portal@example.com")
    # Um morador por mensagem: nunca o e-mail de outro no mesmo envio.
    assert aviso.get_all("To") == ["morador@example.com"]
    assert aviso["Cc"] is None and aviso["Bcc"] is None and aviso["Reply-To"] is None
    assert aviso["Auto-Submitted"] == "auto-generated"
    assert aviso["Message-ID"].endswith("@example.com>")
    assert aviso["Date"]
    assert aviso.get_content_type() == "multipart/alternative"


def test_texto_puro_do_aviso(aviso):
    texto, _ = _partes(aviso)
    assert "Falta d'água no Bloco 1" in texto
    assert "Urgente · para o Bloco 1" in texto
    assert PUBLICACAO in texto
    # Em texto puro, o aviso vai como foi escrito: as marcas são legíveis.
    assert "A **água** volta às 18h.\n\n- Encha os baldes" in texto
    assert "Abrir no Portal: https://portal.example.com/avisos/7" in texto
    assert (
        "Você recebe porque cadastrou este e-mail no Portal Capibaribe Prime. Para não receber "
        "mais, apague o e-mail em Minha unidade."
    ) in " ".join(texto.split())


def test_html_do_aviso(aviso):
    _, html = _partes(aviso)
    assert '<html lang="pt-BR">' in html
    assert "Falta d&#x27;água no Bloco 1</h1>" in html
    assert "<strong>água</strong>" in html
    assert ">Encha os baldes</li>" in html
    assert 'href="https://portal.example.com/avisos/7"' in html
    assert ">Abrir no Portal</a>" in html
    assert "Urgente" in html and "Para o Bloco 1" in html
    assert "apague o e-mail em Minha unidade" in html
    assert PUBLICACAO in html
    # Leitor de e-mail no modo escuro: a página é clara de propósito, sem inversão de cor.
    assert '<meta name="color-scheme" content="light">' in html
    assert '<meta name="supported-color-schemes" content="light">' in html


def test_previa_escondida_no_topo_do_html(aviso):
    _, html = _partes(aviso)
    previa = re.search(r'<div style="display:none[^"]*">([^<]*)</div>', html)
    assert previa, html[:600]
    assert previa[1].startswith("A água volta às 18h.")
    assert html.index(previa[0]) < html.index("Portal Capibaribe Prime</td>")


def test_assunto_sem_urgente_e_so_o_titulo():
    geral = AvisoParaNotificar(**{**AVISO.__dict__, "categoria": "geral"})
    assert mensagem_do_aviso(geral, "m@example.com", CONFIG, PUBLICACAO)["Subject"] == (
        "Falta d'água no Bloco 1"
    )


@pytest.mark.parametrize(
    ("papel", "quando", "linha"),
    [
        (Papel.comissao, datetime(2026, 10, 8, 0, 23, tzinfo=UTC), PUBLICACAO),
        (
            Papel.admin,
            datetime(2026, 1, 5, 12, 5, tzinfo=UTC),
            "Publicado pela Administração do Portal em 05/01, às 9h05",
        ),
        (
            Papel.sindico,
            datetime(2026, 3, 1, 2, 0, tzinfo=UTC),
            "Publicado pelo Síndico em 28/02, às 23h00",
        ),
    ],
)
def test_linha_de_publicacao_no_fuso_de_recife(papel, quando, linha):
    assert linha_de_publicacao(papel, quando) == linha


@pytest.mark.parametrize(
    ("para_todos", "blocos", "frase"),
    [(True, (), "para todos os blocos"), (False, (1, 3), "para os Blocos 1 e 3")],
)
def test_destino_por_extenso(para_todos, blocos, frase):
    outro = AvisoParaNotificar(**{**AVISO.__dict__, "para_todos": para_todos, "blocos": blocos})
    texto, _ = _partes(mensagem_do_aviso(outro, "m@example.com", CONFIG, PUBLICACAO))
    assert frase in texto


def test_titulo_com_html_e_quebra_nao_vira_tag_nem_cabecalho():
    perigoso = AvisoParaNotificar(
        **{**AVISO.__dict__, "titulo": "<script>x</script>\r\nBcc: todos@example.com"}
    )
    mensagem = mensagem_do_aviso(perigoso, "m@example.com", CONFIG, PUBLICACAO)
    assert mensagem["Bcc"] is None
    assert "\n" not in mensagem["Subject"] and "\r" not in mensagem["Subject"]
    _, html = _partes(mensagem)
    assert "<script>" not in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html


def test_mensagem_de_recuperacao():
    unidade = UnidadeRef.de_login("1203")
    mensagem = mensagem_de_recuperacao(unidade, TOKEN, "morador@example.com", CONFIG)
    assert mensagem["Subject"] == "Portal Capibaribe Prime: criar senha nova"
    assert mensagem.get_all("To") == ["morador@example.com"]
    assert parseaddr(mensagem["From"]) == ("Portal Capibaribe Prime", "portal@example.com")
    texto, html = _partes(mensagem)
    link = f"https://portal.example.com/redefinir-senha#token={TOKEN}"
    corrido = " ".join(texto.split())
    assert texto.startswith("Olá!")
    assert (
        "Você (ou alguém da sua família) pediu “Esqueci minha senha” no Portal Capibaribe Prime "
        "para o Bloco 1, apartamento 203."
    ) in corrido
    aviso_de_golpe = (
        "O link abre o Portal do condomínio, em portal.example.com. O Portal nunca pede sua "
        "senha por e-mail nem por WhatsApp."
    )
    assert aviso_de_golpe in corrido
    assert link in texto
    assert "O link vale por 1 hora e só uma vez." in corrido
    assert "Se não foi você, apague este e-mail; sua senha continua a mesma." in corrido
    assert f'href="{link}"' in html
    assert ">Criar senha nova</a>" in html
    assert "1 hora" in html
    assert "Se não foi você, apague este e-mail" in html
    assert "Olá!" in html
    assert "em portal.example.com." in html
    assert "nunca pede sua senha por e-mail nem por WhatsApp" in html
    assert '<meta name="color-scheme" content="light">' in html


def test_senha_de_app_nao_aparece_na_configuracao():
    assert "senha-de-app-falsa" not in repr(CONFIG)
