"""E-mail pelo Gmail do Portal (H-04, H-13; ADR-0006). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.3 e 5. Nesta onda é só o lugar
marcado: o enviador fica desligado até o épico B implementar.

O que o épico B escreve aqui:
- O envio por SMTP (`smtplib.SMTP_SSL` na porta 465, ou STARTTLS na 587, com a
  `config_email()`), com tempo limite, **uma mensagem por unidade** (nunca vários endereços no
  mesmo e-mail: um morador veria o e-mail do outro) e texto puro.
- `ENVIADOR`: implementa `app.servicos.notificacoes.Enviador` com `canal = Canal.email`.
  `ligado()` = `config_email() is not None`. `enviar()` manda a cópia do aviso para
  `destinos_email(db, aviso)`, só até `cota_email_avisos(db)`; o resto conta como `pulados`. O
  link do e-mail é `config_email().url_base + aviso.caminho`.
- O e-mail do "esqueci a senha" (usado por `app/servicos/recuperacao.py`).
"""

from sqlalchemy.orm import Session

from app.modelos import Canal
from app.servicos.notificacoes import AvisoParaNotificar, Resultado


class EnviadorEmail:
    canal = Canal.email

    def ligado(self) -> bool:
        # Épico B: `return config_email() is not None`.
        return False

    def enviar(self, db: Session, aviso: AvisoParaNotificar, resultado: Resultado) -> None:
        raise NotImplementedError("Cópia do aviso por e-mail: épico B do M2")


ENVIADOR = EnviadorEmail()
