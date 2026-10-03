# ADR-0006 · Notificações por Web Push, com e-mail pelo Gmail como reserva

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Avisos precisam chegar ao celular (RF-11) sem custo. O autor decidiu por custo zero, sem
domínio próprio (ADR-0008), o que inviabiliza serviços de e-mail transacional que exigem
domínio verificado.

## Decisão
- **Web Push** padrão (chaves VAPID, biblioteca `pywebpush`), uma inscrição por aparelho
  conectado. Envio em paralelo; inscrição que o serviço diz expirada é removida.
- **E-mail** pelo SMTP do Gmail, numa conta criada só para o Portal, com senha de app. Usado para
  recuperação de senha e cópia de avisos, só para unidades que informaram e-mail.

## Consequências
- Push é grátis e sem limite prático.
- **iPhone só recebe push com o Portal instalado na tela inicial (iOS 16.4 ou mais novo)**, e a
  permissão precisa vir de um toque da pessoa. A tela de instalação terá passo a passo para iPhone.
- Gmail: cerca de 500 envios por dia na conta gratuita, suficiente para 320 unidades. O
  remetente será um endereço `@gmail.com`, menos "oficial" que um domínio próprio.

## Alternativas consideradas
- **Resend / Brevo com domínio próprio:** mais confiável e profissional, mas exige domínio
  (R$ 40/ano), recusado pelo autor em 02/10/2026. Se o domínio vier, trocar o SMTP é uma
  mudança de configuração.
- **Só push, sem e-mail:** deixaria sem recuperação de senha quem não tem o Portal instalado.
