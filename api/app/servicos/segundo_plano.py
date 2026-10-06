"""Trabalho depois da resposta (spec do M2, seção 5; ADR-0010). Arquivo comum.

**Na Vercel:** `vercel.functions.wait_until` (SDK oficial `vercel`, runtime Python ≥ 0.18). A
resposta sai na hora e a mesma invocação continua viva até o trabalho terminar, limitada pela
duração máxima da função (300 s no Hobby com Fluid compute). O trabalho é síncrono (SQLAlchemy,
`smtplib`, `requests`), então vai como `asyncio.to_thread(...)`, como o SDK manda.

**Fora da Vercel** (uvicorn local, testes): `BackgroundTasks` do FastAPI, que roda depois de a
resposta ser enviada. Não dá para usar `wait_until` aqui: sem o contexto do runtime ele não
roda nada (fecha a corrotina em silêncio).

Quem agenda abre a própria sessão de banco dentro do trabalho: a da requisição já fechou.
"""

import asyncio
import os
from collections.abc import Callable

from fastapi import BackgroundTasks


def na_vercel() -> bool:
    # Variável de sistema da Vercel (a mesma que `app.seguranca.ip` usa).
    return os.environ.get("VERCEL") == "1"


def agendar(tarefas: BackgroundTasks, funcao: Callable[..., None], *argumentos: object) -> None:
    """Roda `funcao(*argumentos)` depois da resposta. Não espera e não levanta: o que der
    errado lá dentro é problema de quem escreveu `funcao` (que registra a própria falha)."""
    if na_vercel():
        from vercel.functions import wait_until

        wait_until(asyncio.to_thread(funcao, *argumentos))
    else:
        tarefas.add_task(funcao, *argumentos)
