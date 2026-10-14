"""Validação dos corpos das enquetes (spec do M4, seção 3.2), sem banco."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.esquemas.enquetes import EditarEnquete, MostrarResultado, NovaEnquete, Votar


def _daqui(**delta) -> str:
    return (datetime.now(UTC) + timedelta(**delta)).isoformat()


BASE = {
    "pergunta": "Qual o melhor dia para a reunião com a construtora?",
    "opcoes": ["Terça à noite", "Quinta à noite", "Sábado de manhã"],
    "encerra_em": _daqui(days=7),
    "para_todos": True,
}


def _mensagens(erro: ValidationError) -> list[str]:
    return [e["msg"].removeprefix("Value error, ") for e in erro.errors()]


def test_padroes():
    enquete = NovaEnquete(**BASE)
    assert enquete.multipla_escolha is False
    assert enquete.mostrar_resultado is MostrarResultado.durante
    assert enquete.blocos == []


def test_pergunta_e_opcoes_sem_espacos_nas_pontas_e_brancas_descartadas():
    enquete = NovaEnquete(**{**BASE, "pergunta": "  Qual?  ", "opcoes": [" Sim ", "", "  ", "Não"]})
    assert enquete.pergunta == "Qual?"
    assert enquete.opcoes == ["Sim", "Não"]


@pytest.mark.parametrize(
    ("troca", "mensagem"),
    [
        ({"pergunta": "   "}, "Escreva a pergunta."),
        ({"pergunta": "x" * 201}, "A pergunta pode ter até 200 letras."),
        ({"pergunta": "Qual‮?"}, "Tem um caractere invisível no texto. Apague e escreva de novo."),
        ({"opcoes": ["Sim"]}, "Escreva pelo menos 2 opções de resposta."),
        ({"opcoes": ["Sim", "  "]}, "Escreva pelo menos 2 opções de resposta."),
        ({"opcoes": [f"Opção {n}" for n in range(11)]}, "O limite é de 10 opções."),
        ({"opcoes": ["Sim", "x" * 101]}, "Cada opção pode ter até 100 letras."),
        ({"opcoes": ["Sábado de manhã", "sábado  de MANHÃ"]}, "Duas opções estão iguais."),
        ({"encerra_em": "2030-01-01T20:00:00"}, "Informe a hora com o fuso (ex.: -03:00)."),
        (
            {"encerra_em": _daqui(minutes=-1)},
            "A data de término já passou. Escolha uma data no futuro.",
        ),
        ({"encerra_em": _daqui(days=367)}, "A enquete pode durar até 1 ano."),
        # Folga da API sobre o banco (366 dias e "no futuro" pelo relógio do banco): o que a API
        # aceita, o banco aceita (revisão do contrato, achado 6).
        ({"encerra_em": _daqui(days=365, hours=1)}, "A enquete pode durar até 1 ano."),
        ({"encerra_em": _daqui(minutes=30)}, "Escolha um término daqui a pelo menos 1 hora."),
        ({"para_todos": False}, "Escolha pelo menos um bloco, ou Todos os blocos."),
    ],
)
def test_nova_enquete_recusa(troca, mensagem):
    with pytest.raises(ValidationError) as erro:
        NovaEnquete(**{**BASE, **troca})
    assert mensagem in _mensagens(erro.value)


def test_dez_opcoes_e_um_ano_passam():
    NovaEnquete(
        **{**BASE, "opcoes": [f"Opção {n}" for n in range(10)], "encerra_em": _daqui(days=365)}
    )


def test_blocos_so_quando_nao_e_para_todos():
    assert NovaEnquete(**{**BASE, "blocos": [2, 1]}).blocos == []
    assert NovaEnquete(**{**BASE, "para_todos": False, "blocos": [2, 1, 2]}).blocos == [1, 2]
    with pytest.raises(ValidationError):
        NovaEnquete(**{**BASE, "para_todos": False, "blocos": [10]})


def test_campo_desconhecido_recusado():
    with pytest.raises(ValidationError):
        NovaEnquete(**{**BASE, "sobra": 1})


def test_editar_nao_tem_destino():
    dados = {k: v for k, v in BASE.items() if k != "para_todos"}
    assert EditarEnquete(**dados).pergunta == BASE["pergunta"]
    with pytest.raises(ValidationError):
        EditarEnquete(**dados, para_todos=True)
    with pytest.raises(ValidationError):
        EditarEnquete(**{**dados, "opcoes": ["Só uma"]})


@pytest.mark.parametrize(
    ("opcoes", "mensagem"),
    [
        ([], "Escolha uma opção."),
        ([1, 1], "A mesma opção foi escolhida duas vezes."),
    ],
)
def test_votar_recusa(opcoes, mensagem):
    with pytest.raises(ValidationError) as erro:
        Votar(opcoes=opcoes)
    assert mensagem in _mensagens(erro.value)


def test_votar_mais_de_dez_em_portugues():
    with pytest.raises(ValidationError) as erro:
        Votar(opcoes=list(range(1, 12)))
    assert _mensagens(erro.value) == ["Escolha no máximo 10 opções."]


@pytest.mark.parametrize("opcoes", [[0], [2**63], ["a"]])
def test_votar_ids_validos(opcoes):
    with pytest.raises(ValidationError):
        Votar(opcoes=opcoes)


def test_votar_varias():
    assert Votar(opcoes=[3, 1]).opcoes == [3, 1]
