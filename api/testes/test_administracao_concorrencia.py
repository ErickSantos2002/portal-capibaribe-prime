"""Revisão do M1, C5: impasse (40P01) ou falha de serialização (40001) nas rotas de papéis e de
voltar para a senha inicial viram 409 "tente de novo", não 500.

O erro é gerado de verdade pelo Postgres, na mesma sessão da rota (`raise ... using errcode`),
no meio do serviço: assim o caminho testado é o mesmo de um impasse real entre dois admins.
O último teste faz a corrida de verdade (dois admins tirando o papel um do outro ao mesmo
tempo) e só exige que nenhuma resposta seja 500.
"""

import threading

import pytest
from sqlalchemy import text

from app.servicos import administracao as servico
from testes.test_administracao_apoio import ADMIN, COMISSAO, COMUM

MENSAGEM = "Outra pessoa mexeu nesta unidade ao mesmo tempo. Tente de novo."


def _falhar_com(codigo: str):
    def falhar(db, *_args, **_kwargs):
        db.execute(
            text(f"do $$ begin raise exception 'simulado' using errcode = '{codigo}'; end $$")
        )

    return falhar


@pytest.mark.parametrize("codigo", ["40P01", "40001"])
@pytest.mark.parametrize(
    ("funcao", "metodo", "caminho", "corpo"),
    [
        ("retirar_papel", "DELETE", f"/api/admin/unidades/{COMISSAO}/papeis/comissao", None),
        ("dar_papel", "PUT", f"/api/admin/unidades/{COMUM}/papeis/comissao", None),
        ("resetar", "POST", f"/api/admin/unidades/{COMUM}/resetar", {"confirmo": True}),
    ],
)
def test_impasse_vira_409(predio, logar, monkeypatch, codigo, funcao, metodo, caminho, corpo):
    monkeypatch.setattr(servico, funcao, _falhar_com(codigo))
    resposta = logar(ADMIN).request(metodo, caminho, json=corpo)
    assert resposta.status_code == 409, resposta.text
    assert resposta.json() == {"codigo": "tente_de_novo", "mensagem": MENSAGEM}


def _tirar(cliente, login: str, barreira: threading.Barrier, respostas: list[int]) -> None:
    barreira.wait()
    respostas.append(cliente.delete(f"/api/admin/unidades/{login}/papeis/admin").status_code)


def test_dois_admins_tirando_o_papel_um_do_outro_nunca_da_500(predio, logar):
    """Corrida de verdade: com o trigger do último admin, os dois pedidos se travam e o Postgres
    derruba um deles com 40P01 (visto acontecer antes da correção, como 500)."""
    admin = logar(ADMIN)
    assert admin.put(f"/api/admin/unidades/{COMISSAO}/papeis/admin").status_code == 200
    outro = logar(COMISSAO)
    for _ in range(5):
        respostas: list[int] = []
        barreira = threading.Barrier(2)
        linhas = [
            threading.Thread(target=_tirar, args=(admin, COMISSAO, barreira, respostas)),
            threading.Thread(target=_tirar, args=(outro, ADMIN, barreira, respostas)),
        ]
        for linha in linhas:
            linha.start()
        for linha in linhas:
            linha.join()
        assert set(respostas) <= {200, 403, 409}, respostas
        # Recompõe os dois admins para a próxima rodada, pelo admin que sobrou.
        restante = next(c for c in (admin, outro) if c.get("/api/acesso/eu").json()["admin"])
        for login in (ADMIN, COMISSAO):
            assert restante.put(f"/api/admin/unidades/{login}/papeis/admin").status_code == 200
