"""Minha opinião, corrigir o prestador e avisar a gestão, pela API (spec de 18/10/2026, seções
3.2 e 4)."""

import threading
import time

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.esquemas.indicacoes import AvisarGestao
from app.seguranca.dependencias import Logado
from app.servicos import indicacoes as servico
from testes.apoio_indicacoes import (
    esconder_opiniao_no_banco,
    esconder_prestador_no_banco,
    indicar,
)
from testes.conftest import ADMIN, COMISSAO, COMUM

pytestmark = pytest.mark.usefixtures("predio")


def _opinioes(engine, prestador: int) -> list[tuple[int, bool, str | None]]:
    with engine.connect() as con:
        return [
            tuple(linha)
            for linha in con.execute(
                text(
                    "select unidade_id, recomenda, comentario from opiniao_servico"
                    " where prestador_id = :p order by unidade_id"
                ),
                {"p": prestador},
            )
        ]


def _avisos(engine, prestador: int) -> list[tuple[int, str | None]]:
    with engine.connect() as con:
        return [
            tuple(linha)
            for linha in con.execute(
                text(
                    "select unidade_id, motivo from aviso_servico where prestador_id = :p"
                    " order by id"
                ),
                {"p": prestador},
            )
        ]


def _historico(engine, acao: str) -> list[dict]:
    with engine.connect() as con:
        return [
            dict(linha._mapping)
            for linha in con.execute(
                text(
                    "select unidade_id, entidade, entidade_id, detalhes from historico"
                    " where acao = :a order by id"
                ),
                {"a": acao},
            )
        ]


def _erro(resposta) -> tuple[int, str]:
    return resposta.status_code, resposta.json()["codigo"]


def test_dar_e_mudar_a_opiniao(logar, engine_app, predio):
    p = indicar(logar(ADMIN))
    comum = logar(COMUM)
    r = comum.put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": True})
    assert r.status_code == 200 and r.json()["recomendam"] == 2
    r = comum.put(
        f"/api/indicacoes/{p}/opiniao", json={"recomenda": False, "comentario": "  Atrasou  "}
    )
    corpo = r.json()
    assert (corpo["recomendam"], corpo["nao_recomendam"]) == (1, 1)
    assert corpo["minha_opiniao"] == {
        "recomenda": False,
        "comentario": "Atrasou",
        "escondida": False,
    }
    # Mudada, ela sobe para o topo (a mais recente).
    assert corpo["opinioes"][0]["minha"] is True
    assert [u for u, _, _ in _opinioes(engine_app, p)].count(predio[COMUM]) == 1


@pytest.mark.parametrize("rodada", range(3))
def test_dois_aparelhos_ao_mesmo_tempo_uma_opiniao_so(
    logar, engine_app, predio, monkeypatch, rodada
):
    p = indicar(logar(ADMIN))
    original = servico._opiniao_da_unidade
    vez = iter([0.4, 0.0])
    trava = threading.Lock()

    def devagar(*args, **kwargs):
        # Os dois leem "sem opinião"; o primeiro demora para inserir, o segundo chega no meio.
        achada = original(*args, **kwargs)
        with trava:
            espera = next(vez, 0.0)
        time.sleep(espera)
        return achada

    monkeypatch.setattr(servico, "_opiniao_da_unidade", devagar)
    aparelhos = [logar(COMUM), logar(COMUM)]
    barreira = threading.Barrier(2)
    status: list = [None, None]

    def opinar(i: int) -> None:
        barreira.wait()
        status[i] = (
            aparelhos[i].put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": i == 0}).status_code
        )

    fios = [threading.Thread(target=opinar, args=(i,)) for i in (0, 1)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    assert sorted(status) == [200, 200]
    assert [u for u, _, _ in _opinioes(engine_app, p)].count(predio[COMUM]) == 1


def test_apagar_a_minha_opiniao_e_registrar(logar, engine_app, predio):
    p = indicar(logar(ADMIN))
    comum = logar(COMUM)
    comum.put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": True, "comentario": "Bom"})
    assert comum.delete(f"/api/indicacoes/{p}/opiniao").status_code == 204
    assert predio[COMUM] not in [u for u, _, _ in _opinioes(engine_app, p)]
    registro = _historico(engine_app, "indicacao_opiniao_apagada")
    assert registro == [
        {"unidade_id": predio[COMUM], "entidade": "prestador", "entidade_id": p, "detalhes": {}}
    ]
    assert comum.get(f"/api/indicacoes/{p}").json()["minha_opiniao"] is None
    # Sem opinião, apagar de novo é 404.
    assert _erro(comum.delete(f"/api/indicacoes/{p}/opiniao")) == (404, "opiniao_nao_encontrada")


def test_opiniao_escondida_nao_muda_nem_apaga(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    esconder_opiniao_no_banco(engine_app, p, predio[COMUM], predio[COMISSAO])
    comum = logar(COMUM)
    r = comum.put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": False})
    assert _erro(r) == (409, "opiniao_escondida")
    assert "A gestão escondeu a sua opinião" in r.json()["mensagem"]
    assert _erro(comum.delete(f"/api/indicacoes/{p}/opiniao")) == (409, "opiniao_escondida")
    assert _opinioes(engine_app, p) == [(predio[COMUM], True, "Fez a cozinha no prazo.")]


def test_minha_opiniao_escondida_aparece_so_para_mim(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    logar(ADMIN).put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": True})
    esconder_opiniao_no_banco(engine_app, p, predio[COMUM], predio[COMISSAO])
    eu = logar(COMUM).get(f"/api/indicacoes/{p}").json()
    assert eu["minha_opiniao"] == {
        "recomenda": True,
        "comentario": "Fez a cozinha no prazo.",
        "escondida": True,
    }
    assert all(not o["minha"] for o in eu["opinioes"]) and len(eu["opinioes"]) == 1
    outro = logar(ADMIN).get(f"/api/indicacoes/{p}").json()
    assert [o["unidade"]["login"] for o in outro["opinioes"]] == [ADMIN]
    assert outro["recomendam"] == 1


def test_corrigir_quem_indicou_e_gestao_sim_outro_nao(logar, engine_app):
    p = indicar(logar(COMUM))
    corpo = {"categoria_id": 5, "nome": "Marcenaria Exemplo Ltda", "telefone": "81 3333-4444"}
    r = logar(COMUM).put(f"/api/indicacoes/{p}", json=corpo)
    assert r.status_code == 200, r.text
    assert (r.json()["nome"], r.json()["telefone"], r.json()["celular"]) == (
        "Marcenaria Exemplo Ltda",
        "8133334444",
        False,
    )
    assert r.json()["categoria"]["nome"] == "Eletricista"
    r = logar(COMISSAO).put(f"/api/indicacoes/{p}", json={**corpo, "instagram": "@marcenaria.x"})
    assert r.status_code == 200 and r.json()["instagram"] == "marcenaria.x"
    with engine_app.connect() as con:
        busca = con.execute(text("select nome_busca from prestador where id = :p"), {"p": p})
        assert busca.scalar_one() == "marcenaria exemplo ltda"


def test_outro_morador_nao_corrige(logar):
    p = indicar(logar(ADMIN))
    # Uma unidade comum que não indicou: 403.
    r = logar(COMUM).put(
        f"/api/indicacoes/{p}",
        json={"categoria_id": 1, "nome": "Outro nome", "telefone": "81999990001"},
    )
    assert _erro(r) == (403, "sem_permissao")
    assert logar(COMUM).get(f"/api/indicacoes/{p}").json()["pode_corrigir"] is False


def test_corrigir_para_telefone_de_outro_da_409_com_id(logar):
    comum = logar(COMUM)
    a = indicar(comum, telefone="81999990001")
    b = indicar(comum, telefone="81999990002", nome="Outro")
    r = comum.put(
        f"/api/indicacoes/{b}",
        json={"categoria_id": 1, "nome": "Outro", "telefone": "+55 (81) 9 9999-0001"},
    )
    assert r.status_code == 409 and r.json()["codigo"] == "prestador_ja_existe"
    assert r.json()["id"] == a
    # O próprio telefone continua valendo.
    r = comum.put(
        f"/api/indicacoes/{b}",
        json={"categoria_id": 1, "nome": "Outro", "telefone": "81 99999-0002"},
    )
    assert r.status_code == 200


def test_avisar_uma_vez_aberto_por_unidade(logar, engine_app, predio):
    p = indicar(logar(ADMIN))
    comum = logar(COMUM)
    assert (
        comum.post(f"/api/indicacoes/{p}/aviso", json={"motivo": "Número errado"}).status_code
        == 204
    )
    assert comum.post(f"/api/indicacoes/{p}/aviso", json={"motivo": "De novo"}).status_code == 204
    assert _avisos(engine_app, p) == [(predio[COMUM], "Número errado")]
    assert logar(COMISSAO).post(f"/api/indicacoes/{p}/aviso").status_code == 204
    assert len(_avisos(engine_app, p)) == 2
    assert comum.get(f"/api/indicacoes/{p}").json()["ja_avisei"] is True
    assert logar(ADMIN).get(f"/api/indicacoes/{p}").json()["ja_avisei"] is False


def test_aviso_para_a_gestao_sem_placa(logar, predio):
    p = indicar(logar(ADMIN))
    logar(COMUM).post(f"/api/indicacoes/{p}/aviso", json={"motivo": "Não atende"})
    gestao = logar(COMISSAO).get(f"/api/indicacoes/{p}").json()
    assert [(a["motivo"]) for a in gestao["avisos"]] == ["Não atende"]
    assert "1203" not in str(gestao["avisos"]) and "unidade" not in gestao["avisos"][0]
    assert logar(COMUM).get(f"/api/indicacoes/{p}").json()["avisos"] is None


def test_primeiro_aviso_aberto_devolve_o_id(logar, engine_app, predio):
    p = indicar(logar(ADMIN))

    def logado(login: str) -> Logado:
        return Logado(0, predio[login], login, int(login[0]), login[1:], frozenset(), False)

    with Session(engine_app) as db:
        primeiro = servico.avisar(db, logado(COMUM), p, AvisarGestao())
    with Session(engine_app) as db:
        segundo = servico.avisar(db, logado(COMISSAO), p, AvisarGestao())
    with Session(engine_app) as db:
        repetido = servico.avisar(db, logado(COMUM), p, AvisarGestao())
    assert isinstance(primeiro, int) and segundo is None and repetido is None


def test_motivo_com_301_letras_422(logar):
    p = indicar(logar(ADMIN))
    r = logar(COMUM).post(f"/api/indicacoes/{p}/aviso", json={"motivo": "a" * 301})
    assert r.status_code == 422 and r.json()["campos"][0]["campo"] == "motivo"


def test_prestador_escondido_404_para_morador_nas_quatro_rotas(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    esconder_prestador_no_banco(engine_app, p, predio[COMISSAO])
    comum = logar(COMUM)
    respostas = [
        comum.put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": True}),
        comum.delete(f"/api/indicacoes/{p}/opiniao"),
        comum.put(
            f"/api/indicacoes/{p}",
            json={"categoria_id": 1, "nome": "Outro", "telefone": "81999990001"},
        ),
        comum.post(f"/api/indicacoes/{p}/aviso"),
    ]
    assert [_erro(r) for r in respostas] == [(404, "indicacao_nao_encontrada")] * 4


def test_gestao_nao_muda_prestador_escondido(logar, engine_app, predio):
    p = indicar(logar(COMUM))
    esconder_prestador_no_banco(engine_app, p, predio[COMISSAO])
    r = logar(ADMIN).put(
        f"/api/indicacoes/{p}",
        json={"categoria_id": 1, "nome": "Outro", "telefone": "81999990001"},
    )
    assert _erro(r) == (409, "prestador_escondido")
    r = logar(ADMIN).put(f"/api/indicacoes/{p}/opiniao", json={"recomenda": True})
    assert _erro(r) == (409, "prestador_escondido")


def test_opiniao_sem_recomenda_422(logar):
    p = indicar(logar(ADMIN))
    assert logar(COMUM).put(f"/api/indicacoes/{p}/opiniao", json={}).status_code == 422
