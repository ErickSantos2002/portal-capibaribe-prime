"""Épico B do M2 · Esqueci a senha (H-04). Pertence ao épico B.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.3; spec do épico:
`docs/superpowers/specs/m2-email.md`. Esquemas em `app/esquemas/recuperacao.py`; regras em
`app/servicos/recuperacao.py`. As rotas são finas: chamam o serviço, fazem o commit e gravam o
cookie.

**Sem sessão** (quem esqueceu a senha não entrou), mas **com** `X-Portal: 1`: sem ele, outro
site faria o navegador do morador pedir links (encher a caixa dele, gastar a cota do Gmail) ou
trocar a senha com um token roubado num formulário escondido.

- `POST /api/acesso/recuperacao`           → 202 `RecuperacaoPedida` (sempre a mesma resposta)
- `POST /api/acesso/recuperacao/conferir`  → 200 `LinkValido` · 410 `link_invalido`
- `POST /api/acesso/recuperacao/redefinir` → 200 `Eu` + cookie novo · 410 `link_invalido`

**O pedido não abre o banco** (revisão do contrato, achado 3): a rota só valida o formato do
login e agenda `processar_pedido` para depois da resposta. Consultar a unidade, a cota ou gravar
o token aqui faria o tempo de resposta revelar quem tem e-mail. Não acrescentar `Banco` nela.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.configuracao import config_email
from app.esquemas.comum import Eu
from app.esquemas.recuperacao import (
    MSG_PEDIDO,
    LinkDeRecuperacao,
    LinkValido,
    PedirRecuperacao,
    RecuperacaoPedida,
    RedefinirSenha,
)
from app.seguranca.dependencias import Banco, exige_cabecalho_portal
from app.seguranca.sessoes import gravar_cookie
from app.servicos import recuperacao as servico
from app.servicos import segundo_plano
from app.servicos.email import ASSUNTO_DA_RECUPERACAO

rotas = APIRouter(prefix="/api/acesso/recuperacao", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.post("", status_code=202)
def pedir(dados: PedirRecuperacao, tarefas: BackgroundTasks) -> RecuperacaoPedida:
    segundo_plano.agendar(tarefas, servico.processar_pedido, dados.login)
    # Só a configuração (variáveis de ambiente), nunca o banco: igual para qualquer login.
    config = config_email()
    return RecuperacaoPedida(
        mensagem=MSG_PEDIDO,
        remetente=config.usuario if config else None,
        assunto=ASSUNTO_DA_RECUPERACAO,
    )


@rotas.post("/conferir")
def conferir(dados: LinkDeRecuperacao, db: Banco) -> LinkValido:
    return LinkValido(unidade=servico.conferir(db, dados.token))


@rotas.post("/redefinir")
def redefinir(dados: RedefinirSenha, request: Request, resposta: Response, db: Banco) -> Eu:
    eu, token = servico.redefinir(db, dados, request.headers.get("user-agent"))
    db.commit()
    gravar_cookie(resposta, token)
    return eu
