"""Épico B do M4 · votar e trocar o voto (H-21, RN-01, RN-02).

Contrato: `docs/superpowers/specs/m4-contrato.md`, seções 2.6 e 3; spec do épico:
`docs/superpowers/specs/m4-votar.md`. O banco já tem os próprios testes de burla
(`test_m4_banco.py`); aqui é o caminho da API, inclusive a ordem da gravação com duas
requisições em paralelo da mesma unidade (critério de pronto do marco).
"""

import threading
import time
from datetime import timedelta

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.servicos import enquetes as servico
from testes.apoio import restricao, rodar_alembic
from testes.apoio_m4 import votos_da_enquete
from testes.conftest import BANCO, apagar_banco, garantir_papeis, recriar_banco, url_para
from testes.test_enquetes_voto_apoio import (
    ADMIN,
    COMISSAO,
    COMUM,
    nova,
    vencer,
    votar_no_banco,
)

pytestmark = pytest.mark.usefixtures("predio")


def _votar(cliente, enquete: int, *opcoes: int):
    return cliente.put(f"/api/enquetes/{enquete}/voto", json={"opcoes": list(opcoes)})


def _ok(resposta) -> dict:
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def _erro(resposta) -> tuple[int, str]:
    return resposta.status_code, resposta.json()["codigo"]


# --- votar e trocar -----------------------------------------------------------------------------


def test_votar_responde_a_enquete_com_o_voto(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    a, b, _ = criada.opcoes
    enquete = _ok(_votar(logar(COMUM), criada.id, b))
    assert enquete["id"] == criada.id
    assert enquete["meu_voto"] == [b]
    assert enquete["ja_votou"] is True
    assert enquete["votado_em"] is not None
    assert enquete["participacao"]["votaram"] == 1
    assert [o["votos"] for o in enquete["opcoes"]] == [0, 1, 0]
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [b])]


def test_trocar_o_voto_vale_o_ultimo(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    a, b, _ = criada.opcoes
    comum = logar(COMUM)
    primeiro = _ok(_votar(comum, criada.id, a))
    segundo = _ok(_votar(comum, criada.id, b))
    assert segundo["meu_voto"] == [b]
    assert [o["votos"] for o in segundo["opcoes"]] == [0, 1, 0]
    assert segundo["participacao"]["votaram"] == 1
    assert segundo["votado_em"] >= primeiro["votado_em"]
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [b])]


def test_outro_celular_da_mesma_unidade_ve_e_troca(logar, engine_app, predio):
    """H-21: a esposa do Rafael votou no outro celular; ele vê o voto da unidade e troca."""
    criada = nova(engine_app, predio)
    a, b, _ = criada.opcoes
    esposa, rafael = logar(COMUM), logar(COMUM)
    _ok(_votar(esposa, criada.id, a))
    assert _ok(rafael.get(f"/api/enquetes/{criada.id}"))["meu_voto"] == [a]
    _ok(_votar(rafael, criada.id, b))
    assert _ok(esposa.get(f"/api/enquetes/{criada.id}"))["meu_voto"] == [b]
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [b])]


def test_votar_de_novo_na_mesma_opcao_nao_muda_nada(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    comum = logar(COMUM)
    _ok(_votar(comum, criada.id, criada.opcoes[0]))
    enquete = _ok(_votar(comum, criada.id, criada.opcoes[0]))
    assert enquete["participacao"]["votaram"] == 1
    assert [o["votos"] for o in enquete["opcoes"]] == [1, 0, 0]


def test_multipla_escolha_aceita_varias(logar, engine_app, predio):
    criada = nova(engine_app, predio, multipla=True)
    a, b, c = criada.opcoes
    comum = logar(COMUM)
    assert sorted(_ok(_votar(comum, criada.id, c, a))["meu_voto"]) == [a, c]
    # Trocar na múltipla substitui o conjunto inteiro.
    assert _ok(_votar(comum, criada.id, b))["meu_voto"] == [b]
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [b])]


def test_so_no_fim_responde_sem_os_votos(logar, engine_app, predio):
    criada = nova(engine_app, predio, so_no_fim=True)
    enquete = _ok(_votar(logar(COMUM), criada.id, criada.opcoes[0]))
    assert enquete["meu_voto"] == [criada.opcoes[0]]
    assert [o["votos"] for o in enquete["opcoes"]] == [None, None, None]
    assert enquete["participacao"]["votaram"] == 1


def test_voto_nao_vai_para_o_historico(logar, engine_app, predio):
    """Contrato, seção 3.1: registrar cada voto criaria dado sobre o comportamento das pessoas."""
    criada = nova(engine_app, predio)
    contar = text("select count(*) from historico")
    with engine_app.connect() as con:
        antes = con.execute(contar).scalar_one()
    comum = logar(COMUM)
    _ok(_votar(comum, criada.id, criada.opcoes[0]))
    _ok(_votar(comum, criada.id, criada.opcoes[1]))
    with engine_app.connect() as con:
        assert con.execute(contar).scalar_one() == antes


# --- recusas ------------------------------------------------------------------------------------


def test_escolha_unica_com_duas_opcoes_e_422(logar, engine_app, predio):
    criada = nova(engine_app, predio)
    resposta = _votar(logar(COMUM), criada.id, *criada.opcoes[:2])
    assert resposta.status_code == 422
    corpo = resposta.json()
    assert corpo["codigo"] == "dados_invalidos"
    assert corpo["mensagem"] == "Nesta enquete, escolha só uma opção."
    assert [c["campo"] for c in corpo["campos"]] == ["opcoes"]
    assert votos_da_enquete(engine_app, criada.id) == []


@pytest.mark.parametrize("de_onde", ["outra_enquete", "inexistente"])
def test_opcao_que_nao_e_da_enquete_e_409(logar, engine_app, predio, de_onde):
    """A enquete foi editada depois que a tela abriu: as opções de antes não existem mais."""
    criada = nova(engine_app, predio)
    outra = nova(engine_app, predio)
    opcao = outra.opcoes[0] if de_onde == "outra_enquete" else 999999
    assert _erro(_votar(logar(COMUM), criada.id, opcao)) == (409, "enquete_mudou")
    assert votos_da_enquete(engine_app, criada.id) == []


def test_encerrada_nao_recebe_voto_nem_troca(logar, engine_app, engine_superusuario, predio):
    criada = nova(engine_app, predio)
    comum = logar(COMUM)
    _ok(_votar(comum, criada.id, criada.opcoes[0]))
    vencer(engine_superusuario, criada.id)
    assert _erro(_votar(comum, criada.id, criada.opcoes[1])) == (409, "enquete_encerrada")
    assert _erro(_votar(logar(ADMIN), criada.id, criada.opcoes[1])) == (409, "enquete_encerrada")
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [criada.opcoes[0]])]


def test_gestao_fora_do_destino_e_403(logar, engine_app, predio):
    so_do_bloco_1 = nova(engine_app, predio, blocos=(1,))
    resposta = _votar(logar(COMISSAO), so_do_bloco_1.id, so_do_bloco_1.opcoes[0])
    assert _erro(resposta) == (403, "fora_do_destino")
    assert votos_da_enquete(engine_app, so_do_bloco_1.id) == []


def test_comum_fora_do_destino_e_404(logar, engine_app, predio):
    so_do_bloco_2 = nova(engine_app, predio, blocos=(2,))
    resposta = _votar(logar(COMUM), so_do_bloco_2.id, so_do_bloco_2.opcoes[0])
    assert _erro(resposta) == (404, "enquete_nao_encontrada")
    assert _erro(_votar(logar(COMUM), 999999, 1)) == (404, "enquete_nao_encontrada")


# --- o banco é a última trava: as recusas dele viram 4xx, nunca 500 ------------------------------


def test_prazo_pelo_relogio_do_banco(logar, engine_app, engine_superusuario, predio, monkeypatch):
    """A API acha que está aberta (relógio dela atrasado); o banco recusa pelo dele: 409."""
    criada = nova(engine_app, predio)
    vencer(engine_superusuario, criada.id)
    atrasado = servico._agora() - timedelta(hours=1)
    monkeypatch.setattr(servico, "_agora", lambda: atrasado)
    resposta = _votar(logar(COMUM), criada.id, criada.opcoes[0])
    assert _erro(resposta) == (409, "enquete_encerrada")


def test_opcao_que_some_entre_conferir_e_gravar(logar, engine_app, predio, monkeypatch):
    """Sem a conferência da API (ou com uma edição entre ela e a gravação), a chave estrangeira
    do banco recusa a opção de outra enquete: 409, nunca 500."""
    criada = nova(engine_app, predio)
    outra = nova(engine_app, predio)
    monkeypatch.setattr(servico, "_opcoes_da_enquete", lambda _db, _id: set(outra.opcoes))
    resposta = _votar(logar(COMUM), criada.id, outra.opcoes[0])
    assert _erro(resposta) == (409, "enquete_mudou")
    assert votos_da_enquete(engine_app, criada.id) == []


# --- dois celulares da mesma unidade ao mesmo tempo (critério de pronto do M4) -------------------


def _em_paralelo(engine_app, logar, monkeypatch, criada, escolhas):
    """Duas requisições da mesma unidade (duas sessões, como dois celulares) ao mesmo tempo. A
    primeira a gravar demora entre o voto e as opções, para a segunda chegar no meio."""
    original = servico._trocar_opcoes
    vez = iter([0.4, 0.0])
    trava = threading.Lock()

    def devagar(*args, **kwargs):
        with trava:
            espera = next(vez, 0.0)
        time.sleep(espera)
        return original(*args, **kwargs)

    monkeypatch.setattr(servico, "_trocar_opcoes", devagar)
    celulares = [logar(COMUM), logar(COMUM)]
    barreira = threading.Barrier(2)
    respostas: list = [None, None]

    def votar(i: int) -> None:
        barreira.wait()
        respostas[i] = _votar(celulares[i], criada.id, *escolhas[i])

    fios = [threading.Thread(target=votar, args=(i,)) for i in (0, 1)]
    for fio in fios:
        fio.start()
    for fio in fios:
        fio.join()
    return respostas


@pytest.mark.parametrize("rodada", range(3))
def test_dois_celulares_ao_mesmo_tempo_um_voto_so(logar, engine_app, predio, monkeypatch, rodada):
    criada = nova(engine_app, predio, multipla=True)
    a, b, c = criada.opcoes
    respostas = _em_paralelo(engine_app, logar, monkeypatch, criada, [(a, b), (c,)])
    # Nenhum dos dois recebe erro: o segundo espera o primeiro e troca o voto dele.
    assert [r.status_code for r in respostas] == [200, 200], [r.text for r in respostas]
    [(unidade, opcoes)] = votos_da_enquete(engine_app, criada.id)
    assert unidade == predio[COMUM]
    # Inteiras de um dos dois, nunca misturadas.
    assert opcoes in ([a, b], [c])
    enquete = _ok(logar(COMUM).get(f"/api/enquetes/{criada.id}"))
    assert enquete["participacao"]["votaram"] == 1
    assert sum(o["votos"] for o in enquete["opcoes"]) == len(opcoes)


def test_dois_celulares_escolha_unica(logar, engine_app, predio, monkeypatch):
    criada = nova(engine_app, predio)
    a, b, _ = criada.opcoes
    respostas = _em_paralelo(engine_app, logar, monkeypatch, criada, [(a,), (b,)])
    assert [r.status_code for r in respostas] == [200, 200], [r.text for r in respostas]
    [(_, opcoes)] = votos_da_enquete(engine_app, criada.id)
    assert opcoes in ([a], [b])


# --- revisão do épico B -------------------------------------------------------------------------


@pytest.mark.parametrize("opcao", [True, "1", 1.0])
def test_id_da_opcao_e_inteiro_estrito(logar, engine_app, predio, opcao):
    """Revisão, ponto 7: `true`, `"1"` e `1.0` não viram a opção 1."""
    criada = nova(engine_app, predio)
    resposta = _votar(logar(COMUM), criada.id, opcao)
    assert _erro(resposta) == (422, "dados_invalidos")
    assert votos_da_enquete(engine_app, criada.id) == []


def _desativar(engine_dono, login: str) -> None:
    with engine_dono.begin() as con:
        con.execute(text("update unidade set ativa = false where login = :l"), {"l": login})


def test_banco_recusa_voto_de_unidade_desativada(engine_app, engine_dono, predio):
    """Revisão, ponto 3 (migração 0009): só a sessão barrava; o banco, como `app`, aceitava."""
    criada = nova(engine_app, predio)
    _desativar(engine_dono, COMUM)
    with pytest.raises(DBAPIError) as erro:
        votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    assert restricao(erro.value) == "voto_fora_do_destino"
    assert votos_da_enquete(engine_app, criada.id) == []


def test_banco_recusa_troca_de_unidade_desativada(engine_app, engine_dono, predio):
    criada = nova(engine_app, predio)
    votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[0])
    _desativar(engine_dono, COMUM)
    with pytest.raises(DBAPIError) as erro:
        votar_no_banco(engine_app, criada.id, predio[COMUM], criada.opcoes[1])
    assert restricao(erro.value) == "voto_fora_do_destino"
    assert votos_da_enquete(engine_app, criada.id) == [(predio[COMUM], [criada.opcoes[0]])]


def test_desativada_no_meio_do_voto_e_4xx(logar, engine_dono, engine_app, predio, monkeypatch):
    """A sessão ainda valia quando a requisição entrou; o banco recusa e a API traduz (não 500)."""
    criada = nova(engine_app, predio)
    original = servico._gravar_voto

    def desativa_antes(db, *args):
        _desativar(engine_dono, COMUM)
        return original(db, *args)

    monkeypatch.setattr(servico, "_gravar_voto", desativa_antes)
    assert _erro(_votar(logar(COMUM), criada.id, criada.opcoes[0])) == (403, "fora_do_destino")


def test_migracao_0009_volta_e_vai():
    """O downgrade da 0009 devolve a regra da 0008 (sem a conferência de unidade ativa)."""
    nome = f"{BANCO}_0009"
    garantir_papeis()
    recriar_banco(nome)
    url = url_para("dono", nome)
    corpo = "select prosrc from pg_proc where proname = 'voto_conferir'"
    try:
        rodar_alembic(url, "upgrade", "head")
        with psycopg.connect(url) as con:
            assert "ativa" in con.execute(corpo).fetchone()[0]
        rodar_alembic(url, "downgrade", "0008")
        with psycopg.connect(url) as con:
            assert "ativa" not in con.execute(corpo).fetchone()[0]
        rodar_alembic(url, "upgrade", "head")
    finally:
        apagar_banco(nome)
