"""Como foi a notificação de um aviso (H-13; spec do M2, seção 4.4). Arquivo comum.

- `GET /api/avisos/{aviso_id}/envios` → `EnviosDoAviso` (`Gestao`): um item por canal, na
  ordem push, e-mail. É a medida de entrega ("chegou a quantos aparelhos?"); só contagens.

Fica fora de `app/rotas/avisos.py` para os épicos do M2 não precisarem mexer lá.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import case, select

from app.esquemas.comum import EnvioDoAviso, EnviosDoAviso
from app.modelos import Aviso, Canal, NotificacaoEnvio
from app.seguranca.dependencias import Banco, Gestao, exige_cabecalho_portal
from app.servicos.avisos import nao_encontrado

rotas = APIRouter(prefix="/api/avisos", dependencies=[Depends(exige_cabecalho_portal)])

_ORDEM = case({Canal.push.value: 0, Canal.email.value: 1}, value=NotificacaoEnvio.canal)


@rotas.get("/{aviso_id}/envios")
def envios(aviso_id: int, _: Gestao, db: Banco) -> EnviosDoAviso:
    if db.get(Aviso, aviso_id) is None:
        raise nao_encontrado()
    linhas = db.scalars(
        select(NotificacaoEnvio).where(NotificacaoEnvio.aviso_id == aviso_id).order_by(_ORDEM)
    )
    return EnviosDoAviso(
        itens=[EnvioDoAviso.model_validate(linha, from_attributes=True) for linha in linhas]
    )
