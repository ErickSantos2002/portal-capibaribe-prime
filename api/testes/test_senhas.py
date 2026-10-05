"""Senhas em Argon2id (ADR-0005)."""

from app.seguranca import senhas


def test_hash_e_conferencia():
    h = senhas.gerar_hash("segredo-123")
    assert h.startswith("$argon2id$")
    assert "segredo-123" not in h
    assert senhas.senha_confere(h, "segredo-123")
    assert not senhas.senha_confere(h, "segredo-124")


def test_hash_invalido_nao_levanta():
    assert not senhas.senha_confere("h", "qualquer")
    assert not senhas.senha_confere("", "qualquer")


def test_conferir_sem_unidade_gasta_o_tempo_e_devolve_falso():
    # Login inexistente: a resposta não pode chegar mais rápido que a de senha errada.
    assert senhas.conferir_sem_unidade("mudar123") is False


def test_senha_inicial():
    assert senhas.SENHA_INICIAL == "mudar123"
