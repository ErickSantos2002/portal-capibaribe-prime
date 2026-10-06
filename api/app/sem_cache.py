"""`Cache-Control: no-store` em toda resposta da API (revisão do M1, C6).

Quase tudo o que a API devolve depende de quem está logado (mural, aviso, minha unidade,
painel) ou é erro de segurança. Marcar rota por rota já esqueceu os avisos uma vez; aqui vale
para todas, inclusive erros e 404. A rota de diagnóstico continua idêntica a uma rota que não
existe (as duas ganham o mesmo cabeçalho).

Middleware ASGI puro (não `BaseHTTPMiddleware`): só reescreve os cabeçalhos do início da
resposta, sem tocar no corpo.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class SemCache:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                MutableHeaders(scope=mensagem)["Cache-Control"] = "no-store"
            await send(mensagem)

        await self.app(scope, receive, enviar)
