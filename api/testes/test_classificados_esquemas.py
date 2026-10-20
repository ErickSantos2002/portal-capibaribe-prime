"""Entrada dos classificados (spec de 20/10/2026, seção 4): o que a API aceita e como guarda."""

import pytest
from pydantic import ValidationError

from app.esquemas.classificados import EncerrarAnuncio, NovoAnuncio, PedirFoto

BASE = {
    "tipo": "venda",
    "categoria_id": 1,
    "titulo": "Sofá de 3 lugares",
    "contato": "(81) 9 9999-0001",
}


def _mensagens(erro: ValidationError) -> list[str]:
    return [str(e["ctx"]["error"]) if "ctx" in e else e["msg"] for e in erro.errors()]


def test_contato_vira_so_digitos_com_o_nono_digito():
    assert NovoAnuncio(**BASE).contato == "81999990001"
    assert NovoAnuncio(**{**BASE, "contato": "+55 81 9999-0001"}).contato == "81999990001"
    assert NovoAnuncio(**{**BASE, "contato": "(81) 3333-4444"}).contato == "8133334444"


@pytest.mark.parametrize("ruim", ["0819999-0001", "9999-0001", "81 1999-0001", ""])
def test_contato_invalido(ruim):
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "contato": ruim})


def test_titulo_em_nfc_e_sem_espacos_nas_pontas():
    assert NovoAnuncio(**{**BASE, "titulo": "  Café "}).titulo == "Café"


@pytest.mark.parametrize("titulo", ["ab", "x" * 81, "   ", "Sofa​ novo"])
def test_titulo_fora_da_regra(titulo):
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "titulo": titulo})


def test_descricao_aceita_quebra_de_linha_e_so_espaco_vira_nulo():
    assert NovoAnuncio(**{**BASE, "descricao": "Linha 1\nLinha 2"}).descricao == "Linha 1\nLinha 2"
    assert NovoAnuncio(**{**BASE, "descricao": "   "}).descricao is None


def test_descricao_com_1001_letras_e_recusada():
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "descricao": "a" * 1001})


@pytest.mark.parametrize("tipo", ["troca", "doacao"])
def test_preco_so_na_venda(tipo):
    with pytest.raises(ValidationError) as erro:
        NovoAnuncio(**{**BASE, "tipo": tipo, "preco_centavos": 100})
    assert "Só a venda tem preço." in _mensagens(erro.value)
    assert NovoAnuncio(**{**BASE, "tipo": tipo}).preco_centavos is None


@pytest.mark.parametrize("preco", [-1, 10_000_001])
def test_preco_fora_da_faixa(preco):
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "preco_centavos": preco})


def test_preco_no_teto_passa():
    assert NovoAnuncio(**{**BASE, "preco_centavos": 10_000_000}).preco_centavos == 10_000_000


def test_tipo_e_obrigatorio():
    sem = {k: v for k, v in BASE.items() if k != "tipo"}
    with pytest.raises(ValidationError):
        NovoAnuncio(**sem)


def test_ate_4_fotos_sem_repetir():
    assert NovoAnuncio(**{**BASE, "fotos": [3, 1, 2, 4]}).fotos == [3, 1, 2, 4]
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "fotos": [1, 2, 3, 4, 5]})
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "fotos": [1, 1]})


def test_motivo_do_encerramento_na_lista():
    assert EncerrarAnuncio(motivo="doei").motivo == "doei"
    with pytest.raises(ValidationError):
        EncerrarAnuncio(motivo="perdi")


def test_foto_so_imagem_e_ate_10_mb():
    assert PedirFoto(tipo="image/webp", tamanho_bytes=1000).tipo == "image/webp"
    with pytest.raises(ValidationError) as erro:
        PedirFoto(tipo="application/pdf", tamanho_bytes=1000)
    assert "O Portal aceita fotos em JPEG, PNG ou WEBP." in _mensagens(erro.value)
    with pytest.raises(ValidationError):
        PedirFoto(tipo="image/jpeg", tamanho_bytes=10 * 1024 * 1024 + 1)
    with pytest.raises(ValidationError):
        PedirFoto(tipo="image/jpeg", tamanho_bytes=0)


def test_campo_desconhecido_e_recusado():
    with pytest.raises(ValidationError):
        NovoAnuncio(**{**BASE, "situacao": "reservado"})
