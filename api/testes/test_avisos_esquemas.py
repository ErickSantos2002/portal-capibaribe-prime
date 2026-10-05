"""Esquemas do épico C além dos testes do contrato (`test_esquemas.py`)."""

import pytest
from pydantic import ValidationError

from app.esquemas.avisos import NovoAviso


def test_blocos_omitidos_sem_para_todos_e_recusado():
    # Sem `validate_default`, o padrão [] passaria sem validar e o banco recusaria no commit
    # (aviso sem destino), virando erro 500 em vez da mensagem para a pessoa.
    with pytest.raises(ValidationError) as erro:
        NovoAviso(titulo="Título", texto="Texto", para_todos=False)
    mensagens = {e["loc"][-1]: str(e.get("ctx", {}).get("error")) for e in erro.value.errors()}
    assert mensagens == {"blocos": "Escolha pelo menos um bloco, ou Todos os blocos."}


def test_blocos_omitidos_com_para_todos_valem():
    assert NovoAviso(titulo="Título", texto="Texto", para_todos=True).blocos == []
