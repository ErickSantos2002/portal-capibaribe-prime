"""Épico B do M2 · Esqueci a senha (H-04). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.3. Esquemas em
`app/esquemas/recuperacao.py`; regras em `app/servicos/recuperacao.py` (novo). Nesta onda as
rotas respondem 501 `em_construcao`.

**Sem sessão** (quem esqueceu a senha não entrou), mas **com** `X-Portal: 1`: sem ele, outro
site faria o navegador do morador pedir links (encher a caixa dele, gastar a cota do Gmail) ou
trocar a senha com um token roubado num formulário escondido.

- `POST /api/acesso/recuperacao`           → 202 `RecuperacaoPedida` (sempre a mesma resposta)
- `POST /api/acesso/recuperacao/conferir`  → 200 `LinkValido` · 410 `link_invalido`
- `POST /api/acesso/recuperacao/redefinir` → 200 `Eu` + cookie novo · 410 `link_invalido`
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.erros_api import em_construcao
from app.esquemas.comum import Eu
from app.esquemas.recuperacao import (
    LinkDeRecuperacao,
    LinkValido,
    PedirRecuperacao,
    RecuperacaoPedida,
    RedefinirSenha,
)
from app.seguranca.dependencias import Banco, exige_cabecalho_portal

rotas = APIRouter(prefix="/api/acesso/recuperacao", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("", status_code=202)
def pedir(dados: PedirRecuperacao, db: Banco, tarefas: BackgroundTasks) -> RecuperacaoPedida:
    raise em_construcao()


@rotas.post("/conferir")
def conferir(dados: LinkDeRecuperacao, db: Banco) -> LinkValido:
    raise em_construcao()


@rotas.post("/redefinir")
def redefinir(dados: RedefinirSenha, request: Request, resposta: Response, db: Banco) -> Eu:
    raise em_construcao()
