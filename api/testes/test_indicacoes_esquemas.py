"""Entrada das indicações (spec, seção 3.3 e 4): o que a API aceita e como guarda."""

import pytest
from pydantic import ValidationError

from app.esquemas.indicacoes import (
    AvisarGestao,
    CorrigirPrestador,
    DarOpiniao,
    NovaCategoria,
    NovaIndicacao,
)

BASE = {"categoria_id": 1, "nome": "Marcenaria X", "telefone": "81999990001", "recomenda": True}


@pytest.mark.parametrize(
    ("digitado", "guardado"),
    [
        ("(81) 9 9999-0001", "81999990001"),
        ("+55 81 99999-0001", "81999990001"),
        ("81 3333-4444", "8133334444"),
        ("5581999990001", "81999990001"),
        ("55 81 3333-4444", "8133334444"),
    ],
)
def test_telefone_vira_so_digitos(digitado, guardado):
    assert NovaIndicacao(**{**BASE, "telefone": digitado}).telefone == guardado


@pytest.mark.parametrize(
    "ruim", ["81 8999-00011", "0819999-0001", "9999-0001", "(81) 2999-000", "", "abc"]
)
def test_telefone_invalido(ruim):
    with pytest.raises(ValidationError):
        NovaIndicacao(**{**BASE, "telefone": ruim})


def test_corrigir_tambem_normaliza_o_telefone():
    dados = CorrigirPrestador(categoria_id=1, nome="X Y", telefone="+55 (81) 99999-0001")
    assert dados.telefone == "81999990001" and dados.instagram is None


def test_comentario_so_com_espaco_vira_nulo():
    assert DarOpiniao(recomenda=True, comentario="   ").comentario is None


def test_comentario_aceita_quebra_de_linha_e_tira_as_pontas():
    assert DarOpiniao(recomenda=True, comentario="  Bom\nrápido  ").comentario == "Bom\nrápido"


def test_comentario_com_501_letras_e_recusado():
    DarOpiniao(recomenda=True, comentario="a" * 500)
    with pytest.raises(ValidationError):
        DarOpiniao(recomenda=True, comentario="a" * 501)


def test_motivo_ate_300():
    AvisarGestao(motivo="a" * 300)
    assert AvisarGestao().motivo is None
    with pytest.raises(ValidationError):
        AvisarGestao(motivo="a" * 301)


@pytest.mark.parametrize("invisivel", ["​", "‮", "\x00", "­"])
def test_nome_com_caractere_invisivel_e_recusado(invisivel):
    with pytest.raises(ValidationError):
        NovaIndicacao(**{**BASE, "nome": f"Marce{invisivel}naria"})


def test_comentario_com_invisivel_e_recusado():
    with pytest.raises(ValidationError):
        DarOpiniao(recomenda=True, comentario="Bom​")


def test_nome_em_nfc_e_sem_espaco_nas_pontas():
    assert NovaIndicacao(**{**BASE, "nome": "  José  "}).nome == "José"


@pytest.mark.parametrize("nome", ["X", " ", "a" * 81])
def test_nome_fora_do_tamanho(nome):
    with pytest.raises(ValidationError):
        NovaIndicacao(**{**BASE, "nome": nome})


@pytest.mark.parametrize("digitado", ["@marcenaria.x", "marcenaria.x", "  @marcenaria.x "])
def test_instagram_sem_arroba(digitado):
    assert NovaIndicacao(**BASE, instagram=digitado).instagram == "marcenaria.x"


@pytest.mark.parametrize("ruim", ["com espaço", "a" * 31, "@", "https://instagram.com/x"])
def test_instagram_invalido(ruim):
    with pytest.raises(ValidationError):
        NovaIndicacao(**BASE, instagram=ruim)


def test_instagram_vazio_vira_nulo():
    assert NovaIndicacao(**BASE, instagram="  ").instagram is None


def test_recomenda_e_obrigatorio():
    sem = {k: v for k, v in BASE.items() if k != "recomenda"}
    with pytest.raises(ValidationError):
        NovaIndicacao(**sem)
    with pytest.raises(ValidationError):
        DarOpiniao()


def test_campo_desconhecido_e_recusado():
    with pytest.raises(ValidationError):
        NovaIndicacao(**BASE, preco=10)


@pytest.mark.parametrize("nome", ["J", "a" * 41, "  "])
def test_nome_de_categoria(nome):
    with pytest.raises(ValidationError):
        NovaCategoria(nome=nome)
    assert NovaCategoria(nome=" Jardinagem ").nome == "Jardinagem"
