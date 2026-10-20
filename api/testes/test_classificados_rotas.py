"""Anunciar, ler, editar e o ciclo do dono, pela API (spec de 20/10/2026, seções 3, 4 e 8)."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modelos.classificados import AnuncioFoto
from testes.apoio_classificados import (
    NOVO,
    anunciar,
    envelhecer,
    enviar_foto,
    ids_da_lista,
)
from testes.conftest import ADMIN, COMISSAO, COMUM

INDISPONIVEL = "Este anúncio não está mais disponível."


def _vencer(engine_super, anuncio: int, dias: float = 1) -> None:
    envelhecer(engine_super, "anuncio", "vence_em", anuncio, dias)


def _fotos_do(engine, anuncio: int) -> list[int]:
    with Session(engine) as db:
        return list(
            db.scalars(
                select(AnuncioFoto.id)
                .where(AnuncioFoto.anuncio_id == anuncio)
                .order_by(AnuncioFoto.ordem)
            )
        )


# --- anunciar e ler ---------------------------------------------------------------------------


def test_anunciar_com_fotos_a_primeira_e_a_capa(logar, predio, armazenamento):
    dono = logar(COMUM)
    f1, f2 = enviar_foto(dono, armazenamento), enviar_foto(dono, armazenamento)
    a = anunciar(dono, fotos=[f2, f1])
    aberto = logar(ADMIN).get(f"/api/classificados/{a}").json()
    assert [f["id"] for f in aberto["fotos"]] == [f2, f1]
    assert all("/classificados/" in f["url"] for f in aberto["fotos"])
    assert aberto["unidade"] == {"login": COMUM, "bloco": 1, "apartamento": "203"}
    assert aberto["contato"] == "81999990001" and aberto["celular"] is True
    assert aberto["situacao"] == "ativo" and not aberto["vencido"] and not aberto["meu"]
    cartao = logar(ADMIN).get("/api/classificados").json()["itens"][0]
    assert cartao["capa"] == aberto["fotos"][0]["url"]
    assert "Responsável" not in str(aberto) and "Responsável" not in str(cartao)


def test_anunciar_sem_fotos_funciona_com_os_arquivos_desligados(logar, predio):
    a = anunciar(logar(COMUM))
    aberto = logar(COMUM).get(f"/api/classificados/{a}").json()
    assert aberto["fotos"] == [] and aberto["meu"] is True


def test_foto_de_outra_unidade_ou_nao_confirmada_nao_entra(logar, predio, armazenamento):
    alheia = enviar_foto(logar(ADMIN), armazenamento)
    r = logar(COMUM).post("/api/classificados", json={**NOVO, "fotos": [alheia]})
    assert r.status_code == 422 and r.json()["codigo"] == "foto_invalida"
    pendente = (
        logar(COMUM)
        .post("/api/classificados/fotos", json={"tipo": "image/jpeg", "tamanho_bytes": 9})
        .json()["foto_id"]
    )
    r = logar(COMUM).post("/api/classificados", json={**NOVO, "fotos": [pendente]})
    assert r.status_code == 422
    # Nada ficou pela metade.
    assert ids_da_lista(logar(COMUM)) == []


def test_foto_de_um_anuncio_nao_vai_para_outro(logar, predio, armazenamento):
    dono = logar(COMUM)
    f = enviar_foto(dono, armazenamento)
    anunciar(dono, fotos=[f])
    r = dono.post("/api/classificados", json={**NOVO, "titulo": "Outro", "fotos": [f]})
    assert r.status_code == 422


def test_preco_na_doacao_e_422_no_campo(logar, predio):
    r = logar(COMUM).post(
        "/api/classificados", json={**NOVO, "tipo": "doacao", "preco_centavos": 100}
    )
    assert r.status_code == 422
    assert r.json()["campos"] == [{"campo": "preco_centavos", "mensagem": "Só a venda tem preço."}]


def test_categoria_inexistente_422(logar, predio):
    r = logar(COMUM).post("/api/classificados", json={**NOVO, "categoria_id": 999})
    assert r.status_code == 422 and r.json()["codigo"] == "categoria_inexistente"


def test_lista_mais_recente_primeiro_e_renovar_traz_para_cima(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    velho = anunciar(dono, titulo="Mesa de jantar")
    novo = anunciar(dono, titulo="Cadeira de escritório")
    envelhecer(engine_superusuario, "anuncio", "publicado_em", velho, 25)
    assert ids_da_lista(logar(ADMIN)) == [novo, velho]
    _vencer(engine_superusuario, velho)
    assert ids_da_lista(logar(ADMIN)) == [novo]
    assert dono.post(f"/api/classificados/{velho}/renovar").status_code == 200
    assert ids_da_lista(logar(ADMIN)) == [velho, novo]


def test_lista_tem_ativo_e_reservado_mas_nao_encerrado_nem_escondido(logar, predio):
    dono = logar(COMUM)
    ativo = anunciar(dono, titulo="Geladeira")
    reservado = anunciar(dono, titulo="Fogão")
    encerrado = anunciar(dono, titulo="Micro-ondas")
    escondido = anunciar(dono, titulo="Liquidificador")
    dono.post(f"/api/classificados/{reservado}/reservar")
    dono.post(f"/api/classificados/{encerrado}/encerrar", json={"motivo": "vendi"})
    assert logar(COMISSAO).post(f"/api/classificados/{escondido}/esconder").status_code == 204
    lista = logar(ADMIN).get("/api/classificados").json()
    assert [i["id"] for i in lista["itens"]] == [reservado, ativo]
    assert lista["itens"][0]["situacao"] == "reservado"


@pytest.mark.parametrize("termo", ["sofa", "SOFÁ", "  cinza  ", "moveis", "retirar"])
def test_busca_sem_acento_nem_maiuscula(logar, predio, termo):
    a = anunciar(logar(COMUM))
    anunciar(logar(COMUM), titulo="Bicicleta aro 20", descricao=None, categoria_id=8)
    assert ids_da_lista(logar(ADMIN), busca=termo) == [a]


def test_filtro_por_tipo_e_categoria(logar, predio):
    dono = logar(COMUM)
    venda = anunciar(dono)
    doacao = anunciar(dono, tipo="doacao", preco_centavos=None, titulo="Berço", categoria_id=7)
    troca = anunciar(dono, tipo="troca", preco_centavos=None, titulo="Videogame", categoria_id=3)
    leitor = logar(ADMIN)
    assert ids_da_lista(leitor, tipo="doacao") == [doacao]
    assert ids_da_lista(leitor, tipo="troca") == [troca]
    assert ids_da_lista(leitor, categoria=1) == [venda]
    assert ids_da_lista(leitor) == [troca, doacao, venda]
    assert leitor.get("/api/classificados", params={"tipo": "aluguel"}).status_code == 422


def test_meus_tem_todos_os_estados_e_a_lista_conta(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    aberto = anunciar(dono, titulo="Aberto")
    vencido = anunciar(dono, titulo="Vencido")
    encerrado = anunciar(dono, titulo="Encerrado")
    _vencer(engine_superusuario, vencido)
    dono.post(f"/api/classificados/{encerrado}/encerrar", json={"motivo": "desisti"})
    itens = dono.get("/api/classificados/meus").json()["itens"]
    assert [i["id"] for i in itens] == [aberto, vencido, encerrado]
    assert [i["vencido"] for i in itens] == [False, True, False]
    assert dono.get("/api/classificados").json()["meus"] == 3
    assert logar(ADMIN).get("/api/classificados").json()["meus"] == 0
    assert logar(ADMIN).get("/api/classificados/meus").json()["itens"] == []


@pytest.mark.parametrize("estado", ["vencido", "encerrado", "escondido"])
def test_fora_da_lista_so_o_dono_e_a_gestao_abrem(logar, predio, engine_superusuario, estado):
    dono = logar(COMUM)
    a = anunciar(dono)
    if estado == "vencido":
        _vencer(engine_superusuario, a)
    elif estado == "encerrado":
        dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "vendi"})
    else:
        logar(ADMIN).post(f"/api/classificados/{a}/esconder")
    assert dono.get(f"/api/classificados/{a}").status_code == 200
    assert logar(COMISSAO).get(f"/api/classificados/{a}").status_code == 200


def test_outro_morador_recebe_404_com_a_frase(logar, predio, engine_app, engine_superusuario):
    # Uma segunda unidade comum: a 1101 é admin e a 2304 é da Comissão.
    from testes.conftest import NAO_ATIVADA

    with engine_app.begin() as con:
        con.execute(
            text(
                "update unidade set precisa_trocar_senha = false, ativada_em = now(),"
                " responsavel_nome = 'Fictício', celular = '81900000099'"
                " where login = :l"
            ),
            {"l": NAO_ATIVADA},
        )
    vizinho = logar(NAO_ATIVADA)
    dono = logar(COMUM)
    a = anunciar(dono)
    assert vizinho.get(f"/api/classificados/{a}").status_code == 200
    _vencer(engine_superusuario, a)
    r = vizinho.get(f"/api/classificados/{a}")
    assert r.status_code == 404 and r.json()["mensagem"] == INDISPONIVEL
    assert vizinho.post(f"/api/classificados/{a}/aviso", json={}).status_code == 404
    assert vizinho.get("/api/classificados/99999").json()["mensagem"] == INDISPONIVEL


def test_sem_sessao_401_e_id_fora_da_faixa_422(cliente, logar, predio):
    assert cliente.get("/api/classificados").status_code == 401
    assert logar(COMUM).get(f"/api/classificados/{2**63}").status_code == 422


# --- editar -----------------------------------------------------------------------------------


def test_editar_so_o_dono(logar, predio):
    a = anunciar(logar(COMUM))
    novo = {**NOVO, "titulo": "Sofá de 2 lugares"}
    assert logar(ADMIN).put(f"/api/classificados/{a}", json=novo).status_code == 403
    r = logar(COMUM).put(f"/api/classificados/{a}", json=novo)
    assert r.status_code == 200 and r.json()["titulo"] == "Sofá de 2 lugares"


def test_editar_tira_poe_e_reordena_as_fotos(logar, predio, armazenamento, engine_app):
    dono = logar(COMUM)
    f1, f2, f3 = (enviar_foto(dono, armazenamento) for _ in range(3))
    a = anunciar(dono, fotos=[f1, f2])
    with Session(engine_app) as db:
        chave1 = db.get_one(AnuncioFoto, f1).chave
    r = dono.put(f"/api/classificados/{a}", json={**NOVO, "fotos": [f3, f2]})
    assert r.status_code == 200, r.text
    assert [f["id"] for f in r.json()["fotos"]] == [f3, f2]
    assert _fotos_do(engine_app, a) == [f3, f2]
    # A que saiu foi apagada do bucket de verdade.
    assert f"classificados/{chave1}" not in armazenamento.objetos


def test_editar_sem_fotos_tira_todas(logar, predio, armazenamento, engine_app):
    dono = logar(COMUM)
    a = anunciar(dono, fotos=[enviar_foto(dono, armazenamento)])
    assert dono.put(f"/api/classificados/{a}", json={**NOVO, "fotos": []}).status_code == 200
    assert _fotos_do(engine_app, a) == []
    assert not any(k.startswith("classificados/") for k in armazenamento.objetos)


def test_quinta_foto_e_recusada(logar, predio, armazenamento):
    dono = logar(COMUM)
    fotos = [enviar_foto(dono, armazenamento) for _ in range(5)]
    r = dono.post("/api/classificados", json={**NOVO, "fotos": fotos})
    assert r.status_code == 422


def test_vencido_nao_edita_nem_reserva(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    a = anunciar(dono)
    _vencer(engine_superusuario, a)
    r = dono.put(f"/api/classificados/{a}", json=NOVO)
    assert r.status_code == 409 and r.json()["codigo"] == "anuncio_vencido"
    r = dono.post(f"/api/classificados/{a}/reservar")
    assert r.status_code == 409 and r.json()["codigo"] == "anuncio_vencido"


# --- o ciclo do dono --------------------------------------------------------------------------


def test_reservar_liberar_e_encerrar(logar, predio):
    dono = logar(COMUM)
    a = anunciar(dono)
    assert dono.post(f"/api/classificados/{a}/reservar").json()["situacao"] == "reservado"
    assert dono.post(f"/api/classificados/{a}/liberar").json()["situacao"] == "ativo"
    fim = dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "troquei"}).json()
    assert fim["situacao"] == "encerrado" and fim["motivo_encerramento"] == "troquei"


@pytest.mark.parametrize("acao", ["reservar", "liberar", "renovar"])
def test_so_o_dono_mexe(logar, predio, acao):
    a = anunciar(logar(COMUM))
    r = logar(ADMIN).post(f"/api/classificados/{a}/{acao}")
    assert r.status_code == 403 and r.json()["codigo"] == "sem_permissao"
    r = logar(ADMIN).post(f"/api/classificados/{a}/encerrar", json={"motivo": "vendi"})
    assert r.status_code == 403


def test_encerrado_nao_volta(logar, predio):
    dono = logar(COMUM)
    a = anunciar(dono)
    dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "vendi"})
    for acao in ("reservar", "liberar", "renovar"):
        r = dono.post(f"/api/classificados/{a}/{acao}")
        assert r.status_code == 409 and r.json()["codigo"] == "anuncio_encerrado", acao
    r = dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "doei"})
    assert r.status_code == 409
    assert dono.put(f"/api/classificados/{a}", json=NOVO).status_code == 409


def test_renovar_fora_da_janela_e_409_e_dentro_passa(logar, predio, engine_superusuario):
    dono = logar(COMUM)
    a = anunciar(dono)
    assert dono.get(f"/api/classificados/{a}").json()["pode_renovar"] is False
    r = dono.post(f"/api/classificados/{a}/renovar")
    assert r.status_code == 409 and r.json()["codigo"] == "renovar_cedo"
    # A 5 dias de vencer.
    envelhecer(engine_superusuario, "anuncio", "vence_em", a, -5)
    assert dono.get(f"/api/classificados/{a}").json()["pode_renovar"] is True
    renovado = dono.post(f"/api/classificados/{a}/renovar").json()
    assert renovado["renovado_em"] is not None and renovado["pode_renovar"] is False


def test_escondido_o_dono_ve_e_so_encerra(logar, predio):
    dono = logar(COMUM)
    a = anunciar(dono)
    logar(ADMIN).post(f"/api/classificados/{a}/esconder")
    aberto = dono.get(f"/api/classificados/{a}").json()
    assert aberto["escondido"] is True and aberto["pode_renovar"] is False
    for acao in ("reservar", "renovar"):
        r = dono.post(f"/api/classificados/{a}/{acao}")
        assert r.status_code == 409 and r.json()["codigo"] == "anuncio_escondido"
    assert dono.put(f"/api/classificados/{a}", json=NOVO).status_code == 409
    assert (
        dono.post(f"/api/classificados/{a}/encerrar", json={"motivo": "desisti"}).status_code == 200
    )


def test_limites_viram_429(logar, predio):
    dono = logar(COMUM)
    for n in range(5):
        anunciar(dono, titulo=f"Coisa número {n}")
    r = dono.post("/api/classificados", json={**NOVO, "titulo": "A sexta"})
    assert r.status_code == 429 and r.json()["codigo"] == "limite_do_dia"


def test_fixo_sem_whatsapp(logar, predio):
    a = anunciar(logar(COMUM), contato="(81) 3333-4444")
    aberto = logar(ADMIN).get(f"/api/classificados/{a}").json()
    assert aberto["contato"] == "8133334444" and aberto["celular"] is False
