"""Revisão independente do M1, épico C pela API: C4, U1 e U5.

- C4: aviso arquivado não recebe versão nova, nem quando o arquivamento chega entre a conferência
  da aplicação e a gravação (o banco recusa; a API responde 409, não 500).
- U1: quem leu uma versão anterior vê "corrigido desde a leitura" até abrir de novo; a primeira
  leitura continua contando (quem leu não muda).
- U5: "quem leu" separa quem ainda não entrou no Portal de quem entrou e não leu.
"""

import pytest
from sqlalchemy import text

from app.servicos import avisos as servico
from testes.test_avisos_apoio import ADMIN, COMISSAO, COMUM, NAO_ATIVADA, publicar

pytestmark = pytest.mark.usefixtures("predio")


def _corrigir(cliente, aviso_id: int, titulo: str = "Corrigido"):
    return cliente.put(f"/api/avisos/{aviso_id}", json={"titulo": titulo, "texto": "Texto novo."})


# --- C4 ---------------------------------------------------------------------------------------


def test_c4_arquivado_entre_a_conferencia_e_a_gravacao_vira_409(logar, monkeypatch):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    assert comissao.post(f"/api/avisos/{aviso['id']}/arquivar").status_code == 200
    # Simula a corrida: a conferência da aplicação passou antes de o outro arquivar.
    monkeypatch.setattr(servico, "_recusar_arquivado", lambda *_: None)
    resposta = _corrigir(comissao, aviso["id"])
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["codigo"] == "aviso_arquivado"
    assert resposta.json()["mensagem"] == "Aviso arquivado não pode ser corrigido."


# --- U1 ---------------------------------------------------------------------------------------


def _item(cliente, aviso_id: int) -> dict:
    return next(i for i in cliente.get("/api/avisos").json()["itens"] if i["id"] == aviso_id)


def test_u1_leu_versao_anterior_ve_corrigido_ate_abrir_de_novo(logar, engine_app, predio):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    comum = logar(COMUM)
    assert _item(comum, aviso["id"])["corrigido_desde_a_leitura"] is False
    assert comum.post(f"/api/avisos/{aviso['id']}/lido").status_code == 204
    with engine_app.connect() as con:
        lido_em = con.execute(
            text("select lido_em from aviso_leitura where unidade_id = :u"), {"u": predio[COMUM]}
        ).scalar_one()

    assert _corrigir(comissao, aviso["id"]).status_code == 200
    item = _item(comum, aviso["id"])
    assert (item["lido"], item["corrigido_desde_a_leitura"]) == (True, True)
    assert comum.get(f"/api/avisos/{aviso['id']}").json()["corrigido_desde_a_leitura"] is True

    assert comum.post(f"/api/avisos/{aviso['id']}/lido").status_code == 204
    item = _item(comum, aviso["id"])
    assert (item["lido"], item["corrigido_desde_a_leitura"]) == (True, False)
    with engine_app.connect() as con:
        linha = con.execute(
            text("select lido_em, versao_lida from aviso_leitura where unidade_id = :u"),
            {"u": predio[COMUM]},
        ).one()
    # A primeira leitura continua sendo a que conta.
    assert (linha.lido_em, linha.versao_lida) == (lido_em, 2)


def test_u1_quem_nunca_leu_nao_ve_corrigido(logar):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    _corrigir(comissao, aviso["id"])
    item = _item(logar(COMUM), aviso["id"])
    assert (item["lido"], item["corrigido_desde_a_leitura"]) == (False, False)


def test_u1_quem_leu_conta_igual_depois_da_correcao(logar):
    comissao = logar(COMISSAO)
    aviso = publicar(comissao)
    logar(COMUM).post(f"/api/avisos/{aviso['id']}/lido")
    _corrigir(comissao, aviso["id"])
    leitura = logar(ADMIN).get(f"/api/avisos/{aviso['id']}/leitura").json()
    assert leitura["lidos"] == 2


# --- U5 ---------------------------------------------------------------------------------------


def test_u5_separa_quem_nao_entrou_de_quem_entrou_e_nao_leu(logar):
    aviso = publicar(logar(COMISSAO), para_todos=False, blocos=[1, 4])
    leitura = logar(ADMIN).get(f"/api/avisos/{aviso['id']}/leitura").json()
    assert "nao_leram" not in leitura
    entraram = [u["login"] for u in leitura["entraram_sem_ler"]]
    nao_entraram = [u["login"] for u in leitura["nao_entraram"]]
    # Bloco 1: 1101 (admin) e 1203 entraram; 2304 (Comissão, que publicou) é do Bloco 2.
    assert entraram == [ADMIN, COMUM]
    assert NAO_ATIVADA in nao_entraram
    assert ADMIN not in nao_entraram and COMUM not in nao_entraram
    assert len(nao_entraram) + len(entraram) == leitura["total"] - leitura["lidos"] == 128
    assert nao_entraram == sorted(nao_entraram)


def test_u5_quem_leu_sai_das_duas_listas(logar):
    aviso = publicar(logar(COMISSAO))
    logar(COMUM).post(f"/api/avisos/{aviso['id']}/lido")
    leitura = logar(ADMIN).get(f"/api/avisos/{aviso['id']}/leitura").json()
    assert COMUM not in [u["login"] for u in leitura["entraram_sem_ler"]]
    assert [u["login"] for u in leitura["entraram_sem_ler"]] == [ADMIN]
