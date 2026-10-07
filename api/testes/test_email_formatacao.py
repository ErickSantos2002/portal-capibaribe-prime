"""O texto do aviso no e-mail (spec do épico B, seção 2.4): o mesmo Markdown restrito do front,
convertido para HTML com todo o texto escapado.

Os casos de `analisar` e `trechos` são os de `web/src/avisos/formatacao.test.ts`: se o front
mudar, este teste mostra onde o e-mail ficou para trás.
"""

import re

import pytest

from app.servicos.email import analisar, html_do_texto, trechos

# --- paridade com o front (formatacao.test.ts) ------------------------------------------------


def test_paragrafos_por_linha_em_branco():
    assert analisar("Linha 1\nLinha 2\n\n  \nParte 2") == [
        {"tipo": "paragrafo", "linhas": ["Linha 1", "Linha 2"]},
        {"tipo": "paragrafo", "linhas": ["Parte 2"]},
    ]


def test_titulo():
    assert analisar("## Como entrar\nCada apartamento tem uma conta.") == [
        {"tipo": "titulo", "texto": "Como entrar"},
        {"tipo": "paragrafo", "linhas": ["Cada apartamento tem uma conta."]},
    ]


def test_lista():
    assert analisar("Leve:\n- Documento\n- Sapato fechado\nAté lá.") == [
        {"tipo": "paragrafo", "linhas": ["Leve:"]},
        {"tipo": "lista", "itens": ["Documento", "Sapato fechado"]},
        {"tipo": "paragrafo", "linhas": ["Até lá."]},
    ]


def test_numerada_comeca_do_primeiro_numero():
    assert analisar("1. Entrar\n2. Trocar a senha") == [
        {"tipo": "numerada", "inicio": 1, "itens": ["Entrar", "Trocar a senha"]}
    ]
    assert analisar("3. Terceiro\n4. Quarto") == [
        {"tipo": "numerada", "inicio": 3, "itens": ["Terceiro", "Quarto"]}
    ]


def test_destaque():
    assert analisar("> Vagas limitadas.\n> Confirme até quinta.\n\nFim.") == [
        {"tipo": "destaque", "linhas": ["Vagas limitadas.", "Confirme até quinta."]},
        {"tipo": "paragrafo", "linhas": ["Fim."]},
    ]


def test_linha_em_branco_separa_listas_e_quebras_de_linha():
    assert analisar("- a\n\n- b") == [
        {"tipo": "lista", "itens": ["a"]},
        {"tipo": "lista", "itens": ["b"]},
    ]
    assert analisar("a\r\nb\r\rc") == [
        {"tipo": "paragrafo", "linhas": ["a", "b"]},
        {"tipo": "paragrafo", "linhas": ["c"]},
    ]
    assert analisar("x - item") == [
        {"tipo": "paragrafo", "linhas": ["x"]},
        {"tipo": "lista", "itens": ["item"]},
    ]


@pytest.mark.parametrize(
    "linha",
    [
        "#Título",
        "# Título",
        "### Título",
        "##Título",
        "## ",
        "-item",
        "- ",
        "* item",
        "1.item",
        "1) item",
        "1234. item",
        ">destaque",
        "> ",
        "  - recuado",
        "| a | b |",
        "```código```",
        "١. item",
    ],
)
def test_marca_malformada_fica_como_texto(linha):
    assert analisar(linha) == [{"tipo": "paragrafo", "linhas": [linha]}]


def test_trechos_negrito_e_links():
    assert trechos("Não se **perde mais** no grupo.") == [
        {"texto": "Não se "},
        {"texto": "perde mais", "negrito": True},
        {"texto": " no grupo."},
    ]
    assert trechos("Veja https://exemplo.com.br/a. Ou **http://b.org**") == [
        {"texto": "Veja "},
        {"texto": "https://exemplo.com.br/a", "link": "https://exemplo.com.br/a"},
        {"texto": ". Ou "},
        {"texto": "http://b.org", "link": "http://b.org", "negrito": True},
    ]


@pytest.mark.parametrize("linha", ["**sem fim", "** espaço **", "****", "*itálico*"])
def test_negrito_malformado_fica_literal(linha):
    assert trechos(linha) == [{"texto": linha}]


def test_caractere_de_direcao_nao_entra_no_link():
    partes = trechos("https://a.com/‮gpj.exe")
    assert partes[0] == {"texto": "https://a.com/", "link": "https://a.com/"}


def test_link_so_http():
    for linha in ["JAVASCRIPT:alert(1)", "ftp://x.org", "httpx://x.org", "https://"]:
        assert not any("link" in p for p in trechos(linha))


# --- HTML ------------------------------------------------------------------------------------


def _sem_estilo(html: str) -> str:
    """O HTML sem os atributos de estilo, para comparar a estrutura."""
    return re.sub(r' style="[^"]*"', "", html)


def test_cada_marca_vira_a_tag_certa():
    texto = (
        "## Obra\nA **água** volta às 18h.\n\n- Bloco 1\n- Bloco 2\n\n3. três\n4. quatro\n\n"
        "> Atenção.\n> Prazo sexta."
    )
    assert _sem_estilo(html_do_texto(texto)) == (
        "<h2>Obra</h2>"
        "<p>A <strong>água</strong> volta às 18h.</p>"
        "<ul><li>Bloco 1</li><li>Bloco 2</li></ul>"
        '<ol start="3"><li>três</li><li>quatro</li></ol>'
        "<blockquote>Atenção.<br>Prazo sexta.</blockquote>"
    )


def test_link_vira_ancora_com_o_endereco():
    assert _sem_estilo(html_do_texto("Veja https://exemplo.com/a?b=1&c=2.")) == (
        '<p>Veja <a href="https://exemplo.com/a?b=1&amp;c=2">https://exemplo.com/a?b=1&amp;c=2</a>.</p>'
    )


ATAQUES = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<b>negrito</b>",
    '<a href="javascript:alert(1)">x</a>',
    "[clique](javascript:alert(1))",
    "## <script>x</script>\n- <img onerror=y>\n> <iframe src=//evil>",
    "**<svg onload=alert(1)>**",
    'https://exemplo.com/"onmouseover="alert(1)',
    "https://exemplo.com/<script>",
]


@pytest.mark.parametrize("ataque", ATAQUES)
def test_html_injetado_no_aviso_sai_escapado(ataque):
    html = html_do_texto(ataque)
    # Só as tags que o próprio Portal escreve; nenhuma que veio do texto.
    tags = set(re.findall(r"<\s*/?\s*([a-zA-Z0-9]+)", html))
    assert tags <= {"p", "br", "strong", "a", "h2", "ul", "ol", "li", "blockquote"}
    assert "javascript:" not in re.sub(
        r"&[a-z]+;", "", " ".join(re.findall(r'href="([^"]*)"', html))
    )
    for perigoso in ("<script", "<img", "<iframe", "<svg"):
        assert perigoso not in html
    # Dentro das tags, só os atributos que o Portal escreve (nada de `onerror`, `onload`…).
    for atributos in re.findall(r"<[a-z0-9]+((?:\s[^>]*)?)>", html):
        assert set(re.findall(r'\s([a-zA-Z-]+)="', atributos)) <= {"style", "href", "start"}
        assert not re.search(r"\son[a-z]+\s*=", atributos)
    # Todo href é um endereço http(s) sem aspas dentro.
    for href in re.findall(r'href="([^"]*)"', html):
        assert href.startswith(("https://", "http://"))
        assert '"' not in href and "<" not in href
