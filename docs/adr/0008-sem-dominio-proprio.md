# ADR-0008 · Sem domínio próprio: endereço gratuito da Vercel

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Um domínio `.com.br` custa R$ 40/ano. O autor escolheu manter custo zero (02/10/2026).

## Decisão
Usar o endereço gratuito da Vercel, no formato `<nome-do-projeto>.vercel.app`, com o nome mais
claro disponível (ex.: `portal-capibaribe-prime.vercel.app`).

## Consequências
- Custo zero mantido.
- Link menos "oficial": divulgar pela Comissão, no grupo, com mensagem fixada e print da tela.
- E-mail sai de um `@gmail.com` (ADR-0006).
- **Trocar de endereço depois exige reinstalar o PWA e reavisar todo mundo.** Se o domínio vier,
  o ideal é que venha antes da divulgação ampla.

## Alternativas consideradas
- **Domínio `.com.br` (R$ 40/ano):** recomendado na análise pelo link confiável e pelo e-mail
  profissional; recusado para manter custo zero.
