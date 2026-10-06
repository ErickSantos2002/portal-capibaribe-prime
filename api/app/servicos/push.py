"""Web Push (H-05, H-13; ADR-0006). **Pertence ao épico A** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.2 e 5. Nesta onda é só o lugar
marcado: o enviador fica desligado até o épico A implementar.

O que o épico A escreve aqui:
- `ENVIADOR`: implementa `app.servicos.notificacoes.Enviador` com `canal = Canal.push`.
  `ligado()` = `config_push() is not None`. `enviar()` manda para `destinos_push(db, aviso)` em
  paralelo (pywebpush, VAPID de `config_push()`), com o corpo `PushAviso` (spec, seção 4.2),
  TTL de 3 dias, `Urgency: high` para a categoria `urgente` (`normal` nas outras) e `Topic`
  `aviso-<id>`. Resposta 404 ou 410: apaga a inscrição (`removidas`, que também conta como
  falha). Outro erro: `falhas`, segue para o próximo.
- As funções de inscrição que `app/rotas/push.py` usa (inscrever e remover este aparelho,
  estado das notificações).
"""

from sqlalchemy.orm import Session

from app.modelos import Canal
from app.servicos.notificacoes import AvisoParaNotificar, Resultado


class EnviadorPush:
    canal = Canal.push

    def ligado(self) -> bool:
        # Épico A: `return config_push() is not None`.
        return False

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        raise NotImplementedError("Web Push: épico A do M2")


ENVIADOR = EnviadorPush()
