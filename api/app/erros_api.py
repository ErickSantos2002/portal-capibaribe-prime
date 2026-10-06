"""Formato de erro da API (spec do M1, seção 3.4).

Todo erro previsto responde `{"codigo": ..., "mensagem": ...}` (mais campos extras quando úteis):
`codigo` é estável, para a tela decidir o que fazer; `mensagem` já vem pronta para o morador.

Erro de validação (422) vira `codigo = "dados_invalidos"` com a lista `campos`. O valor
digitado **nunca** volta na resposta: o padrão do FastAPI devolve o `input`, que pode ser uma
senha ou um celular.

401/404/405 do próprio Starlette (rota inexistente, método errado) ficam no formato padrão,
para a rota de diagnóstico do M0 continuar idêntica a uma rota que não existe.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

MENSAGEM_PADRAO = "Confira os campos marcados."

# Tradução das falhas mais comuns do Pydantic. O resto vira "Valor inválido.".
_POR_TIPO = {
    "missing": "Preencha este campo.",
    "string_too_short": "Preencha este campo.",
    "string_too_long": "Texto longo demais.",
}


class ErroApi(Exception):
    """Erro previsto de uma rota. `extras` entram no corpo junto de `codigo` e `mensagem`.

    A mensagem é mostrada ao morador e não vai para a tabela `erro` (não é exceção não
    tratada), mas mesmo assim nunca deve repetir o que a pessoa digitou.
    """

    def __init__(self, status: int, codigo: str, mensagem: str, **extras: Any) -> None:
        super().__init__(codigo)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.extras = extras

    def corpo(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, **self.extras}


def em_construcao() -> ErroApi:
    """Rota já declarada no contrato, ainda sem implementação (ondas de contrato)."""
    return ErroApi(501, "em_construcao", "Esta parte do Portal ainda está sendo feita.")


def _campo(loc: tuple) -> str | None:
    # loc = ("body", "senha") ou ("query", "situacao"); o primeiro item é a origem.
    partes = [str(p) for p in loc[1:]]
    return ".".join(partes) or None


def _mensagem(erro: dict[str, Any]) -> str:
    if erro.get("type") == "value_error":
        causa = (erro.get("ctx") or {}).get("error")
        if causa is not None and str(causa):
            return str(causa)
    return _POR_TIPO.get(erro.get("type", ""), "Valor inválido.")


def campos_invalidos(exc: RequestValidationError) -> list[dict[str, str | None]]:
    campos: list[dict[str, str | None]] = []
    for erro in exc.errors():
        item = {"campo": _campo(tuple(erro.get("loc", ()))), "mensagem": _mensagem(erro)}
        if item not in campos:
            campos.append(item)
    return campos


async def _tratar_erro_api(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ErroApi)
    return JSONResponse(status_code=exc.status, content=exc.corpo())


async def _tratar_validacao(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    campos = campos_invalidos(exc)
    mensagem = str(campos[0]["mensagem"]) if campos else MENSAGEM_PADRAO
    return JSONResponse(
        status_code=422,
        content={"codigo": "dados_invalidos", "mensagem": mensagem, "campos": campos},
    )


def instalar_tratadores(app: FastAPI) -> None:
    app.add_exception_handler(ErroApi, _tratar_erro_api)
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
