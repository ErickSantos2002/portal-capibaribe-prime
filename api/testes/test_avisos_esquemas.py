"""Esquemas do épico C além dos testes do contrato (`test_esquemas.py`)."""

import pytest
from pydantic import ValidationError

from app.esquemas.avisos import CorrigirAviso, NovoAviso

# --- fechamento do M3: título do aviso com a regra endurecida do épico A (C3) ----------------

INVISIVEIS_NOVOS = [
    " ",  # separador de linha (Zl)
    " ",  # separador de parágrafo (Zp)
    "ㅤ",  # preenchimentos do Hangul
    "ﾠ",
    "ᅟ",
    "ᅠ",
    "؜",  # marca de letra árabe (Cf)
    "᠎",  # separador de vogal mongol (Cf)
    "­",  # hífen invisível (Cf)
]


@pytest.mark.parametrize("invisivel", INVISIVEIS_NOVOS)
@pytest.mark.parametrize("esquema", [NovoAviso, CorrigirAviso])
def test_titulo_do_aviso_recusa_invisivel(esquema, invisivel):
    extra = {"para_todos": True} if esquema is NovoAviso else {}
    with pytest.raises(ValidationError) as erro:
        esquema(titulo=f"Obra{invisivel}de outubro", texto="Texto", **extra)
    assert [e["loc"][-1] for e in erro.value.errors()] == ["titulo"]


def test_titulo_do_aviso_so_com_preenchimento_e_recusado():
    with pytest.raises(ValidationError):
        NovoAviso(titulo="ㅤㅤ", texto="Texto", para_todos=True)


def test_titulo_do_aviso_com_emoji_composto_continua_valendo():
    # O ZWJ (U+200D) junta os emojis de família e de profissão.
    titulo = "Obra \U0001f477‍♀️ e prazos"
    assert NovoAviso(titulo=titulo, texto="Texto", para_todos=True).titulo == titulo


def test_regra_e_a_mesma_do_titulo_do_documento():
    from app.esquemas import comum, documentos

    assert documentos.sem_invisivel_nenhum is comum.sem_invisivel_nenhum


def test_blocos_omitidos_sem_para_todos_e_recusado():
    # Sem `validate_default`, o padrão [] passaria sem validar e o banco recusaria no commit
    # (aviso sem destino), virando erro 500 em vez da mensagem para a pessoa.
    with pytest.raises(ValidationError) as erro:
        NovoAviso(titulo="Título", texto="Texto", para_todos=False)
    mensagens = {e["loc"][-1]: str(e.get("ctx", {}).get("error")) for e in erro.value.errors()}
    assert mensagens == {"blocos": "Escolha pelo menos um bloco, ou Todos os blocos."}


def test_blocos_omitidos_com_para_todos_valem():
    assert NovoAviso(titulo="Título", texto="Texto", para_todos=True).blocos == []
