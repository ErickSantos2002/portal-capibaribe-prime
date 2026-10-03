# ADR-0002 · Hospedagem na Vercel (plano Hobby), front e API no mesmo projeto

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Restrição de custo zero, sem infraestrutura da H&S. A API em Python precisa rodar em algum lugar
sem servidor próprio.

## Decisão
Vercel, plano **Hobby**, num único projeto: o front como arquivos estáticos e a API FastAPI como
Vercel Function (o runtime Python roda apps ASGI direto). As rotas `/api/*` vão para a API, o
resto para o front. Região das funções: **São Paulo** (`gru1`), perto do banco e dos usuários.

## Consequências
- Mesmo domínio para tela e API: cookie de sessão simples e sem CORS.
- Deploy automático a cada push; prévia por branch.
- Limites relevantes (conferidos em 02/10/2026): 4,5 MB por requisição (por isso arquivos vão
  direto ao R2), 300 s por execução, 4 h de CPU ativa por mês, logs guardados só por 1 hora,
  e **uma** regra de limite por IP no firewall.
- Plano Hobby é só para uso **não comercial**: o Portal não cobra nada e ninguém é pago para
  desenvolvê-lo. Se isso mudar, migrar para o Pro.
- API em função serverless não mantém estado entre requisições: nada de cache em memória ou
  tarefa em segundo plano longa.

## Alternativas consideradas
- **Render (grátis):** servidor de verdade, mas dorme após 15 min e demora cerca de um minuto
  para acordar, ruim para a Dona Socorro.
- **VPS da Hostinger (H&S):** descartada pela restrição de não usar infraestrutura do trabalho.
- **Google Cloud Run:** cota grátis generosa, mas exige conta de faturamento e é mais complexo
  de operar sozinho.
