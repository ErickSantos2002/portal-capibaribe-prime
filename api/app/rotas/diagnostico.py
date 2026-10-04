"""Erro forçado, para verificar em produção que exceções chegam à tabela `erro`.

Só dispara com o cabeçalho `X-Portal-Diagnostico` igual à variável `PORTAL_DIAGNOSTICO_SEGREDO`.
Sem a variável, ou com o cabeçalho errado, responde 404, como uma rota que não existe. A
comparação é em tempo constante, para o tempo de resposta não revelar o segredo aos poucos.
"""

import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.servicos.erros import ErroDoPortal

rotas = APIRouter()


class ErroDiagnostico(ErroDoPortal):
    """Exceção de propósito, que nenhum outro código levanta."""


def _segredo_confere(recebido: str | None) -> bool:
    esperado = os.environ.get("PORTAL_DIAGNOSTICO_SEGREDO", "")
    if not esperado or recebido is None:
        return False
    return hmac.compare_digest(recebido.encode(), esperado.encode())


@rotas.post("/api/diagnostico/erro", include_in_schema=False)
def forcar_erro(
    x_portal_diagnostico: Annotated[str | None, Header()] = None,
) -> None:
    if not _segredo_confere(x_portal_diagnostico):
        raise HTTPException(status_code=404, detail="Not Found")
    raise ErroDiagnostico("Erro forçado pela rota de diagnóstico")
