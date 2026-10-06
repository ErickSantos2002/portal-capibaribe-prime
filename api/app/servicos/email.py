"""E-mail pelo Gmail do Portal (H-04, H-13; ADR-0006). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.3 e 5; spec do épico:
`docs/superpowers/specs/m2-email.md`.

- **Texto do aviso em HTML** (`analisar`, `trechos`, `html_do_texto`): porte do Markdown
  restrito do front (`web/src/avisos/formatacao.ts`). Todo texto passa por `html.escape`; só as
  marcas do Portal viram tags, sempre fixas. Mudou o front, mude aqui.
"""

import html
import re
from typing import Any

from sqlalchemy.orm import Session

from app.modelos import Canal
from app.servicos.notificacoes import AvisoParaNotificar, Resultado

# --- Markdown restrito → HTML (spec do épico B, seção 2.4) -------------------------------------

_TITULO = re.compile(r"^## (?=\S)(.*)$")
_ITEM = re.compile(r"^- (?=\S)(.*)$")
_NUMERADO = re.compile(r"^([0-9]{1,3})\. (?=\S)(.*)$")
_DESTAQUE = re.compile(r"^> (?=\S)(.*)$")
_EM_BRANCO = re.compile(r"^[ \t]*$")
_NEGRITO = re.compile(r"\*\*(\S(?:.*?\S)??)\*\*")
_QUEBRA = re.compile(r"\r\n?|[  ]")
# Iguais a `ENDERECO` e `FIM_DE_FRASE` de `web/src/avisos/formatos.ts`.
_ENDERECO = re.compile(r"https?://[^\s<>\"​-‏‪-‮⁠-⁩﻿]+")
_FIM_DE_FRASE = re.compile(r"[.,;:!?)\]}'\"…]+$")

Bloco = dict[str, Any]
Trecho = dict[str, Any]


def analisar(texto: str) -> list[Bloco]:
    """Separa o texto em blocos, linha a linha (mesma saída de `analisar` do front)."""
    blocos: list[Bloco] = []
    separado = True  # a próxima linha começa bloco novo
    for linha in _QUEBRA.sub("\n", texto).split("\n"):
        if _EM_BRANCO.match(linha):
            separado = True
            continue
        anterior = None if separado or not blocos else blocos[-1]
        tipo_anterior = anterior["tipo"] if anterior else None
        separado = False
        if achado := _TITULO.match(linha):
            blocos.append({"tipo": "titulo", "texto": achado[1].rstrip()})
            separado = True
        elif achado := _ITEM.match(linha):
            if anterior and tipo_anterior == "lista":
                anterior["itens"].append(achado[1])
            else:
                blocos.append({"tipo": "lista", "itens": [achado[1]]})
        elif achado := _NUMERADO.match(linha):
            if anterior and tipo_anterior == "numerada":
                anterior["itens"].append(achado[2])
            else:
                blocos.append({"tipo": "numerada", "inicio": int(achado[1]), "itens": [achado[2]]})
        elif achado := _DESTAQUE.match(linha):
            if anterior and tipo_anterior == "destaque":
                anterior["linhas"].append(achado[1])
            else:
                blocos.append({"tipo": "destaque", "linhas": [achado[1]]})
        elif anterior and tipo_anterior == "paragrafo":
            anterior["linhas"].append(linha)
        else:
            blocos.append({"tipo": "paragrafo", "linhas": [linha]})
    return blocos


def _partes_da_linha(linha: str) -> list[Trecho]:
    partes: list[Trecho] = []
    resto = 0
    for achado in _ENDERECO.finditer(linha):
        inicio = achado.start()
        endereco = _FIM_DE_FRASE.sub("", achado[0])
        if len(endereco) <= len("https://"):
            continue
        if inicio > resto:
            partes.append({"texto": linha[resto:inicio]})
        partes.append({"texto": endereco, "link": endereco})
        resto = inicio + len(endereco)
    if resto < len(linha):
        partes.append({"texto": linha[resto:]})
    return partes


def _com_links(texto: str, negrito: bool) -> list[Trecho]:
    return [p | {"negrito": True} if negrito else p for p in _partes_da_linha(texto)]


def trechos(linha: str) -> list[Trecho]:
    """Separa uma linha em texto, negrito e links (mesma saída de `trechos` do front)."""
    resultado: list[Trecho] = []
    resto = 0
    for achado in _NEGRITO.finditer(linha):
        if achado.start() > resto:
            resultado += _com_links(linha[resto : achado.start()], False)
        resultado += _com_links(achado[1], True)
        resto = achado.end()
    if resto < len(linha):
        resultado += _com_links(linha[resto:], False)
    return resultado


# Estilos inline: muito cliente de e-mail ignora `<style>`. Cores dos tokens da casca.
_COR_MATA = "#1f5e3b"
_COR_TINTA = "#17231c"
_COR_IPE = "#e8b22a"
_COR_IPE_SUAVE = "#fbf0cf"
_E = {
    "p": f"margin:0 0 14px;font-size:17px;line-height:1.55;color:{_COR_TINTA}",
    "h2": f"margin:22px 0 8px;font-size:19px;line-height:1.3;color:{_COR_TINTA}",
    "lista": (
        f"margin:0 0 14px;padding-left:24px;font-size:17px;line-height:1.55;color:{_COR_TINTA}"
    ),
    "li": "margin:0 0 4px",
    "destaque": (
        f"margin:0 0 14px;padding:12px 16px;border-left:4px solid {_COR_IPE};"
        f"background:{_COR_IPE_SUAVE};font-size:17px;line-height:1.55;color:{_COR_TINTA}"
    ),
    "a": f"color:{_COR_MATA};text-decoration:underline;word-break:break-all",
}


def _html_da_linha(linha: str) -> str:
    saida = []
    for trecho in trechos(linha):
        conteudo = html.escape(trecho["texto"])
        if "link" in trecho:
            conteudo = f'<a href="{html.escape(trecho["link"])}" style="{_E["a"]}">{conteudo}</a>'
        if trecho.get("negrito"):
            conteudo = f"<strong>{conteudo}</strong>"
        saida.append(conteudo)
    return "".join(saida)


def _html_das_linhas(linhas: list[str]) -> str:
    return "<br>".join(_html_da_linha(linha) for linha in linhas)


def html_do_texto(texto: str) -> str:
    """O texto do aviso em HTML de e-mail. Nada do texto vira tag: tudo é escapado."""
    partes = []
    for bloco in analisar(texto):
        tipo = bloco["tipo"]
        if tipo == "titulo":
            partes.append(f'<h2 style="{_E["h2"]}">{_html_da_linha(bloco["texto"])}</h2>')
        elif tipo in ("lista", "numerada"):
            itens = "".join(
                f'<li style="{_E["li"]}">{_html_da_linha(item)}</li>' for item in bloco["itens"]
            )
            if tipo == "lista":
                partes.append(f'<ul style="{_E["lista"]}">{itens}</ul>')
            else:
                inicio = "" if bloco["inicio"] == 1 else f' start="{bloco["inicio"]}"'
                partes.append(f'<ol{inicio} style="{_E["lista"]}">{itens}</ol>')
        elif tipo == "destaque":
            conteudo = _html_das_linhas(bloco["linhas"])
            partes.append(f'<blockquote style="{_E["destaque"]}">{conteudo}</blockquote>')
        else:
            partes.append(f'<p style="{_E["p"]}">{_html_das_linhas(bloco["linhas"])}</p>')
    return "".join(partes)


# --- cópia do aviso (H-13) ------------------------------------------------------------------


class EnviadorEmail:
    canal = Canal.email

    def ligado(self) -> bool:
        return False

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        raise NotImplementedError("Cópia do aviso por e-mail: épico B do M2")


ENVIADOR = EnviadorEmail()
