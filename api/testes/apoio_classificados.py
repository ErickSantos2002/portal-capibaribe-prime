"""Apoio dos testes dos classificados (spec de 20/10/2026): criar anúncio e foto com SQL direto,
como a API faz, e o mesmo pela API."""

import secrets

from sqlalchemy import text


def categoria_id(con, nome: str = "Móveis") -> int:
    return con.execute(
        text("select id from categoria_classificado where nome = :n"), {"n": nome}
    ).scalar_one()


def criar_anuncio(
    con,
    unidade: int,
    *,
    tipo: str = "venda",
    titulo: str = "Sofá de 3 lugares",
    preco: int | None = 35000,
    contato: str = "81999990001",
    categoria: str = "Móveis",
    descricao: str | None = None,
) -> int:
    return con.execute(
        text(
            "insert into anuncio (unidade_id, categoria_id, tipo, titulo, descricao,"
            " preco_centavos, contato) values (:u, :c, :t, :ti, :d, :p, :ct) returning id"
        ),
        {
            "u": unidade,
            "c": categoria_id(con, categoria),
            "t": tipo,
            "ti": titulo,
            "d": descricao,
            "p": preco,
            "ct": contato,
        },
    ).scalar_one()


def criar_foto(con, unidade: int, *, confirmada: bool = True) -> int:
    foto = con.execute(
        text(
            "insert into anuncio_foto (unidade_id, chave, tipo, bytes)"
            " values (:u, :k, 'image/webp', 1000) returning id"
        ),
        {"u": unidade, "k": secrets.token_hex(16)},
    ).scalar_one()
    if confirmada:
        con.execute(
            text("update anuncio_foto set confirmada_em = now() where id = :f"), {"f": foto}
        )
    return foto


def prender_foto(con, foto: int, anuncio: int, ordem: int) -> None:
    con.execute(
        text("update anuncio_foto set anuncio_id = :a, ordem = :o where id = :f"),
        {"a": anuncio, "o": ordem, "f": foto},
    )


def envelhecer(engine_super, tabela: str, coluna: str, id_: int, dias: float) -> None:
    """Põe a data `dias` no passado, como superusuário e sem as triggers (o `app` nunca consegue:
    as datas são do banco). Para testar vencimento, janela de renovar e faxina."""
    with engine_super.begin() as con:
        con.execute(text(f"alter table {tabela} disable trigger user"))
        con.execute(
            text(f"update {tabela} set {coluna} = now() - make_interval(secs => :s) where id = :i"),
            {"s": dias * 86400, "i": id_},
        )
        con.execute(text(f"alter table {tabela} enable trigger user"))


# --- pela API --------------------------------------------------------------------------------

NOVO = {
    "tipo": "venda",
    "categoria_id": 1,  # Móveis (o `banco_limpo` recarrega na ordem)
    "titulo": "Sofá de 3 lugares",
    "descricao": "Sofá cinza, sem manchas. Retirar no Bloco 1.",
    "preco_centavos": 35000,
    "contato": "(81) 9 9999-0001",
    "fotos": [],
}

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 60
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 60
PDF = b"%PDF-1.4\n" + b"0" * 60


def enviar_foto(cliente, armazenamento, conteudo: bytes = JPEG, tipo: str = "image/jpeg") -> int:
    """Pede, manda ao bucket falso e confirma. Devolve o id da foto (falha se não der 200)."""
    pedido = cliente.post(
        "/api/classificados/fotos", json={"tipo": tipo, "tamanho_bytes": len(conteudo)}
    )
    assert pedido.status_code == 201, pedido.text
    corpo = pedido.json()
    chave = corpo["url"].split("/envios/")[1].split("?")[0]
    armazenamento.receber(chave, conteudo, tipo)
    confirmado = cliente.post(f"/api/classificados/fotos/{corpo['foto_id']}/confirmar")
    assert confirmado.status_code == 200, confirmado.text
    return corpo["foto_id"]


def anunciar(cliente, **campos) -> int:
    resposta = cliente.post("/api/classificados", json={**NOVO, **campos})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()["id"]


def ids_da_lista(cliente, **filtros) -> list[int]:
    resposta = cliente.get("/api/classificados", params=filtros)
    assert resposta.status_code == 200, resposta.text
    return [i["id"] for i in resposta.json()["itens"]]
