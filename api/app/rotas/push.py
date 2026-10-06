"""Épico A do M2 · Notificações no aparelho (H-05). Pertence ao épico A.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.2. Esquemas em
`app/esquemas/push.py`; regras em `app/servicos/push.py`.

- `GET    /api/notificacoes`               → `EstadoNotificacoes` (`UnidadeLogada`)
- `PUT    /api/notificacoes/este-aparelho` → 204; guarda a inscrição da sessão deste aparelho
  (503 `notificacoes_desligadas` sem VAPID; 409 `limite_de_aparelhos` com 10 já inscritos)
- `DELETE /api/notificacoes/este-aparelho` → 204, idempotente
"""

from fastapi import APIRouter, Depends

from app.esquemas.push import EstadoNotificacoes, InscricaoPush
from app.seguranca.dependencias import Banco, UnidadeLogada, exige_cabecalho_portal
from app.servicos import push

# Toda alteração exige `X-Portal: 1` (CSRF, ADR-0005).
rotas = APIRouter(prefix="/api/notificacoes", dependencies=[Depends(exige_cabecalho_portal)])


@rotas.get("")
def estado(logado: UnidadeLogada, db: Banco) -> EstadoNotificacoes:
    return push.estado(db, logado.sessao_id)


@rotas.put("/este-aparelho", status_code=204)
def inscrever(dados: InscricaoPush, logado: UnidadeLogada, db: Banco) -> None:
    push.inscrever(db, logado.sessao_id, dados)


@rotas.delete("/este-aparelho", status_code=204)
def remover(logado: UnidadeLogada, db: Banco) -> None:
    push.remover(db, logado.sessao_id)
