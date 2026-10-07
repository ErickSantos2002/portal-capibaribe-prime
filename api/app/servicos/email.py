"""E-mail pelo Gmail do Portal (H-04, H-13; ADR-0006). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.3 e 5; spec do épico:
`docs/superpowers/specs/m2-email.md`.

- **Texto do aviso em HTML** (`analisar`, `trechos`, `html_do_texto`): porte do Markdown
  restrito do front (`web/src/avisos/formatacao.ts`). Todo texto passa por `html.escape`; só as
  marcas do Portal viram tags, sempre fixas. Mudou o front, mude aqui.
- **Mensagens** (`mensagem_do_aviso`, `mensagem_de_recuperacao`): texto puro + HTML simples, um
  destinatário por mensagem (um morador nunca vê o e-mail do outro), assunto numa linha só.
- **Conexão** (`conexao_smtp`, `enviar_uma`): `SMTP_SSL` na 465 (Gmail) ou STARTTLS nas outras
  portas, certificado conferido, tempo limite, senha de app da `config_email()`.
- **`ENVIADOR`** (cópia do aviso, H-13): reserva a cota **antes** de conectar, manda tudo por
  **uma** conexão, salva o progresso a cada `SALVAR_A_CADA`, para no prazo (`pulados`). Recusa
  de um destinatário é falha daquele destino; o resto interrompe o canal (a peça comum loga só
  o tipo do erro: a mensagem de um erro SMTP pode trazer o e-mail de alguém).
"""

import html
import re
import smtplib
import ssl
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.configuracao import ConfigEmail, config_email
from app.esquemas.comum import UnidadeRef
from app.modelos import Aviso, Canal, Papel
from app.servicos.avisos import ASSINATURAS, resumir
from app.servicos.notificacoes import (
    SALVAR_A_CADA,
    AvisoParaNotificar,
    Resultado,
    destinos_email,
)

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


# --- as mensagens (spec do épico B, seções 2.1 a 2.3) ----------------------------------------

# Nome e cores de cada categoria (`web/src/avisos/categorias.ts` e os tokens `--cat-*`): a
# categoria nunca aparece só pela cor, sempre com o nome.
_CATEGORIAS = {
    "geral": ("Geral", "#4a5a50", "#e9ece9"),
    "obra": ("Obra", "#9c4517", "#f7e6dc"),
    "reuniao": ("Reunião", "#2f5d9e", "#e2eaf6"),
    "financeiro": ("Financeiro", "#1f5e3b", "#e3eee6"),
    "urgente": ("Urgente", "#a3322a", "#f8e4e1"),
}
RODAPE_DO_AVISO = (
    "Você recebe porque cadastrou este e-mail no Portal Capibaribe Prime. Para não receber mais, "
    "apague o e-mail em Minha unidade. Sem e-mail, o “esqueci a senha” também deixa de funcionar."
)
RODAPE_DA_RECUPERACAO = (
    "Mandado pelo Portal Capibaribe Prime porque alguém pediu “Esqueci minha senha” para este "
    "apartamento."
)
_FONTE = "'Atkinson Hyperlegible',Arial,Helvetica,sans-serif"


def _juntar(itens: list[str]) -> str:
    return itens[0] if len(itens) < 2 else f"{', '.join(itens[:-1])} e {itens[-1]}"


def destino_em_texto(aviso: AvisoParaNotificar) -> str:
    """ "para todos os blocos", "para o Bloco 1", "para os Blocos 1 e 3" (como no mural)."""
    if aviso.para_todos or not aviso.blocos:
        return "para todos os blocos"
    numeros = [str(b) for b in aviso.blocos]
    if len(numeros) == 1:
        return f"para o Bloco {numeros[0]}"
    return f"para os Blocos {_juntar(numeros)}"


def _uma_linha(texto: str) -> str:
    """Assunto numa linha só: quebra no título não vira cabeçalho novo."""
    return " ".join(texto.split())


def _mensagem(config: ConfigEmail, para: str, assunto: str, texto: str, html_: str) -> EmailMessage:
    mensagem = EmailMessage()
    mensagem["From"] = formataddr((config.remetente_nome, config.usuario))
    mensagem["To"] = para
    mensagem["Subject"] = _uma_linha(assunto)
    mensagem["Date"] = formatdate(localtime=False)
    mensagem["Message-ID"] = make_msgid(domain=config.usuario.rpartition("@")[2] or None)
    # RFC 3834: respostas automáticas ("estou de férias") não voltam para o Portal.
    mensagem["Auto-Submitted"] = "auto-generated"
    mensagem.set_content(texto)
    mensagem.add_alternative(html_, subtype="html")
    return mensagem


_MOLDURA = {
    # Prévia escondida: aparece na lista de e-mails, não no corpo.
    "previa": (
        "display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;"
        "font-size:1px;line-height:1px;color:#f4f6f2;mso-hide:all"
    ),
    "corpo": f"margin:0;padding:0;background:#f4f6f2;font-family:{_FONTE};color:{_COR_TINTA}",
    "cartao": "max-width:600px;background:#ffffff;border:1px solid #cfd8d1;border-radius:12px",
    "faixa": (
        f"padding:18px 24px;background:{_COR_MATA};border-radius:12px 12px 0 0;"
        "color:#ffffff;font-size:18px;font-weight:bold"
    ),
    "botao": (
        "display:inline-block;padding:14px 28px;color:#ffffff;font-size:18px;"
        "font-weight:bold;text-decoration:none;border-radius:8px"
    ),
    "copiar": "margin:0 0 20px;font-size:14px;line-height:1.5;color:#4a5a50",
    "rodape": (
        "padding:16px 24px 20px;border-top:1px solid #cfd8d1;font-size:14px;"
        "line-height:1.5;color:#4a5a50"
    ),
}


def _pagina(
    titulo: str,
    previa: str,
    miolo: str,
    botao: str,
    endereco: str,
    rodape: str,
    depois: str = "",
) -> str:
    """Moldura do e-mail em HTML: tabela de 600 px, estilos inline, só cores dos tokens.

    - `previa`: a linha que o leitor de e-mail mostra ao lado do assunto, escondida no corpo.
    - `color-scheme: light`: o Portal é claro de propósito; o modo escuro do leitor de e-mail
      não inverte as cores (o verde do botão e o rótulo da categoria continuam legíveis).
    - `depois`: parágrafos depois do botão (o aviso contra golpe, no link de recuperação).
    """
    e, m = html.escape, _MOLDURA
    tabela = 'role="presentation" width="100%" cellpadding="0" cellspacing="0"'
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{e(titulo)}</title></head>
<body style="{m["corpo"]}">
<div style="{m["previa"]}">{e(previa)}</div>
<table {tabela} style="background:#f4f6f2">
<tr><td align="center" style="padding:24px 12px">
<table {tabela} style="{m["cartao"]}">
<tr><td style="{m["faixa"]}">Portal Capibaribe Prime</td></tr>
<tr><td style="padding:24px 24px 8px">
{miolo}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 12px"><tr>
<td style="border-radius:8px;background:{_COR_MATA}">\
<a href="{e(endereco)}" style="{m["botao"]}">{e(botao)}</a></td>
</tr></table>
<p style="{m["copiar"]}">Se o botão não abrir, copie este endereço no navegador:<br>\
<a href="{e(endereco)}" style="{_E["a"]}">{e(endereco)}</a></p>
{depois}
</td></tr>
<tr><td style="{m["rodape"]}">{e(rodape)}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


# Recife não tem horário de verão desde 2019: UTC-3 fixo (sem depender do tzdata do servidor).
FUSO_DE_RECIFE = timezone(timedelta(hours=-3), "America/Recife")
_MASCULINOS = {Papel.sindico, Papel.conselho}


def linha_de_publicacao(publicado_como: Papel, publicado_em: datetime) -> str:
    """ "Publicado pela Comissão em 07/10, às 21h23": a assinatura do mural, no fuso de Recife."""
    quem = ASSINATURAS[publicado_como]
    artigo = "pelo" if publicado_como in _MASCULINOS else "pela"
    quando = publicado_em.astimezone(FUSO_DE_RECIFE)
    return f"Publicado {artigo} {quem} em {quando:%d/%m}, às {quando.hour}h{quando:%M}"


def publicacao_do_aviso(db: Session, aviso_id: int) -> str:
    """A linha de publicação do aviso, lida do banco (quem publicou e quando)."""
    publicado_como, publicado_em = db.execute(
        select(Aviso.publicado_como, Aviso.publicado_em).where(Aviso.id == aviso_id)
    ).one()
    return linha_de_publicacao(Papel(publicado_como), publicado_em)


def assunto_do_aviso(aviso: AvisoParaNotificar) -> str:
    """O título do aviso; "Urgente: " na frente só quando é urgente."""
    return f"Urgente: {aviso.titulo}" if aviso.categoria == "urgente" else aviso.titulo


def mensagem_do_aviso(
    aviso: AvisoParaNotificar, para: str, config: ConfigEmail, publicacao: str
) -> EmailMessage:
    """Cópia do aviso para uma unidade (H-13): um destinatário só."""
    nome, cor, fundo = _CATEGORIAS.get(aviso.categoria, _CATEGORIAS["geral"])
    endereco = config.url_base + aviso.caminho
    destino = destino_em_texto(aviso)
    texto = (
        f"{aviso.titulo}\n{nome} · {destino}\n{publicacao}\n\n{aviso.texto}\n\n"
        f"Abrir no Portal: {endereco}\n\n--\n{RODAPE_DO_AVISO}\n"
    )
    miolo = (
        f'<p style="margin:0 0 10px;font-size:15px;color:#4a5a50">'
        f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        f'background:{fundo};color:{cor};font-weight:bold">{html.escape(nome)}</span>'
        f" &nbsp;{html.escape(destino[0].upper() + destino[1:])}</p>"
        f'<h1 style="margin:0 0 6px;font-size:24px;line-height:1.25;color:{_COR_TINTA}">'
        f"{html.escape(aviso.titulo)}</h1>"
        f'<p style="margin:0 0 18px;font-size:15px;color:#4a5a50">{html.escape(publicacao)}</p>'
        f"{html_do_texto(aviso.texto)}"
    )
    html_ = _pagina(
        aviso.titulo, resumir(aviso.texto), miolo, "Abrir no Portal", endereco, RODAPE_DO_AVISO
    )
    return _mensagem(config, para, assunto_do_aviso(aviso), texto, html_)


def link_de_recuperacao(url_base: str, token: str) -> str:
    """O token vai depois do `#`: o navegador não o manda ao servidor (nem em log, nem em
    `Referer`). O endereço vem sempre da configuração, nunca do cabeçalho `Host`."""
    return f"{url_base}/redefinir-senha#token={token}"


ASSUNTO_DA_RECUPERACAO = "Portal Capibaribe Prime: criar senha nova"


def mensagem_de_recuperacao(
    unidade: UnidadeRef, token: str, para: str, config: ConfigEmail
) -> EmailMessage:
    """O link de "esqueci a senha" (H-04)."""
    endereco = link_de_recuperacao(config.url_base, token)
    placa = f"Bloco {unidade.bloco}, apartamento {unidade.apartamento}"
    pedido = (
        "Você (ou alguém da sua família) pediu “Esqueci minha senha” no Portal Capibaribe "
        f"Prime para o {placa}."
    )
    validade = "O link vale por 1 hora e só uma vez."
    # Contra golpe: o morador aprende onde o link leva e que ninguém pede a senha.
    golpe = (
        f"O link abre o Portal do condomínio, em {urlsplit(config.url_base).netloc}. O Portal "
        "nunca pede sua senha por e-mail nem por WhatsApp."
    )
    nao_foi = "Se não foi você, apague este e-mail; sua senha continua a mesma."
    texto = (
        f"Olá!\n\n{pedido}\n\nPara criar a senha nova, abra este link:\n{endereco}\n\n"
        f"{validade}\n\n{golpe}\n\n{nao_foi}\n\n--\n{RODAPE_DA_RECUPERACAO}\n"
    )
    p = _E["p"]
    miolo = (
        f'<h1 style="margin:0 0 16px;font-size:24px;line-height:1.25;color:{_COR_TINTA}">'
        f"Criar senha nova</h1>"
        f'<p style="{p}">Olá!</p>'
        f'<p style="{p}">{html.escape(pedido)}</p>'
        f'<p style="{p}"><strong>{html.escape(validade)}</strong></p>'
    )
    depois = f'<p style="{p}">{html.escape(golpe)}</p><p style="{p}">{html.escape(nao_foi)}</p>'
    html_ = _pagina(
        "Criar senha nova",
        f"Link para criar a senha nova do {placa}. Vale por 1 hora.",
        miolo,
        "Criar senha nova",
        endereco,
        RODAPE_DA_RECUPERACAO,
        depois,
    )
    return _mensagem(config, para, ASSUNTO_DA_RECUPERACAO, texto, html_)


# --- conexão (spec do épico B, seção 2.1) ---------------------------------------------------

# Segundos de espera por resposta do servidor SMTP (conectar, login, cada mensagem).
TEMPO_LIMITE_SMTP = 20


def _conectar(config: ConfigEmail) -> smtplib.SMTP:
    """Abre e autentica a conexão: TLS direto na 465 (Gmail), STARTTLS nas outras portas.
    Certificado conferido (`ssl.create_default_context`)."""
    contexto = ssl.create_default_context()
    if config.porta == 465:
        conexao: smtplib.SMTP = smtplib.SMTP_SSL(
            config.host, config.porta, timeout=TEMPO_LIMITE_SMTP, context=contexto
        )
    else:
        conexao = smtplib.SMTP(config.host, config.porta, timeout=TEMPO_LIMITE_SMTP)
    try:
        if config.porta != 465:
            conexao.starttls(context=contexto)
        conexao.login(config.usuario, config.senha_app)
    except BaseException:
        _fechar(conexao)
        raise
    return conexao


def _fechar(conexao: smtplib.SMTP) -> None:
    try:
        conexao.quit()
    except Exception:  # noqa: BLE001 - a conexão já caiu: não há o que fechar
        conexao.close()


@contextmanager
def conexao_smtp(config: ConfigEmail) -> Iterator[smtplib.SMTP]:
    """Uma conexão para um lote inteiro de mensagens, fechada no fim (mesmo com erro)."""
    conexao = _conectar(config)
    try:
        yield conexao
    finally:
        _fechar(conexao)


class NadaSaiu(Exception):
    """A conexão (ou o login) falhou antes de mandar qualquer coisa. A causa fica em
    `__cause__`; a mensagem desta exceção é só o tipo dela (nunca endereço nem senha)."""


def enviar_uma(config: ConfigEmail, mensagem: EmailMessage) -> None:
    """Manda uma mensagem só (o link de recuperação), na própria conexão. Se nem conectou,
    levanta `NadaSaiu`: quem chama sabe que a mensagem certamente não saiu."""
    try:
        conexao = _conectar(config)
    except Exception as erro:
        raise NadaSaiu(type(erro).__name__) from erro
    try:
        conexao.send_message(mensagem)
    finally:
        _fechar(conexao)


# --- cópia do aviso (H-13; spec do épico B, seção 2.2) ----------------------------------------

# Recusa do Gmail que vale para a conta inteira (cota do dia, limite de envio): 421 em qualquer
# fase, ou o código estendido 5.4.5 / 4.7.x no texto da resposta.
_RECUSA_DA_CONTA = re.compile(rb"(?<![0-9.])(5\.4\.5|4\.7\.[0-9]{1,3})(?![0-9.])")


def falha_so_deste_destino(erro: Exception) -> bool:
    """Recusa que é só daquele destino (endereço que não existe, mensagem recusada): conta como
    falha e o envio segue. Cota estourada, remetente recusado, conexão que caiu: interrompe
    (continuar seria bater na mesma parede centenas de vezes)."""
    if isinstance(erro, smtplib.SMTPRecipientsRefused):
        return True
    if isinstance(erro, smtplib.SMTPDataError):
        resposta = erro.smtp_error if isinstance(erro.smtp_error, bytes) else b""
        return erro.smtp_code != 421 and not _RECUSA_DA_CONTA.search(resposta)
    return False


class EnviadorEmail:
    canal = Canal.email

    def ligado(self) -> bool:
        return config_email() is not None

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        """Uma mensagem por unidade do destino, todas pela mesma conexão. A cota é reservada
        antes de conectar; o que não cabe nela ou no prazo vira `pulados`. Não faz commit."""
        config = config_email()
        if config is None:
            raise RuntimeError("e-mail desligado")
        destinos = destinos_email(db, aviso)
        resultado.destinos = len(destinos)
        if not destinos:
            return
        cabem = resultado.reservar(len(destinos))
        resultado.pulados += len(destinos) - cabem
        if cabem == 0:
            return
        publicacao = publicacao_do_aviso(db, aviso.aviso_id)
        tentadas = 0
        try:
            with conexao_smtp(config) as conexao:
                for feitos, destino in enumerate(destinos[:cabem]):
                    if resultado.tempo_esgotado():
                        resultado.pulados += cabem - feitos
                        break
                    tentadas += 1
                    try:
                        conexao.send_message(
                            mensagem_do_aviso(aviso, destino.email, config, publicacao)
                        )
                        resultado.entregues += 1
                    except smtplib.SMTPException as erro:
                        if not falha_so_deste_destino(erro):
                            raise
                        resultado.falhas += 1
                    if (feitos + 1) % SALVAR_A_CADA == 0:
                        resultado.salvar()
        except BaseException:
            # O que nem chegou a ser tentado volta para a cota (senha de app errada não prende
            # a cota por 24 h). A mensagem que estava saindo pode ter saído: fica reservada.
            resultado.reservados -= cabem - tentadas
            raise


ENVIADOR = EnviadorEmail()
