"""E-mail pelo Gmail do Portal (H-04, H-13; ADR-0006). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seções 4.3 e 5. Nesta onda é só o lugar
marcado: o enviador fica desligado até o épico B implementar.

O que o épico B escreve aqui:
- O envio por SMTP (`smtplib.SMTP_SSL` na porta 465, ou STARTTLS na 587, com a
  `config_email()`), com tempo limite, **uma mensagem por unidade** (nunca vários endereços no
  mesmo e-mail: um morador veria o e-mail do outro) e texto puro.
- `ENVIADOR`: implementa `app.servicos.notificacoes.Enviador` com `canal = Canal.email`.
  `ligado()` = `config_email() is not None`. `enviar()`:
  1. `destinos = destinos_email(db, aviso)`; `resultado.destinos = len(destinos)`;
  2. `n = resultado.reservar(len(destinos))` **antes de mandar** (reserva a cota do Gmail com
     trava e grava na hora; o banco recusa tentativa além da reserva); os outros
     `len(destinos) - n` são `pulados`;
  3. manda os `n` primeiros, `resultado.salvar()` a cada `SALVAR_A_CADA`; se
     `resultado.tempo_esgotado()`, para e conta o resto como `pulados`.
  O link do e-mail é `config_email().url_base + aviso.caminho`.
- O e-mail do "esqueci a senha" (usado por `app/servicos/recuperacao.py`, que pega a cota com
  `reservar_email_recuperacao(db)` antes de criar o token).
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
