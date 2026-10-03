# ADR-0003 · Banco no Neon (PostgreSQL gerenciado, plano Free)

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
Precisamos de Postgres gerenciado e gratuito, com uso esporádico (picos quando sai aviso).

## Decisão
Neon, plano Free, região São Paulo (se disponível na criação; senão a mais próxima). Conexão
pelo pooler do Neon, porque funções serverless abrem muitas conexões curtas. Dois usuários de
banco: `dono` (só para migrações) e `app` (o que a API usa), com `app` **sem DELETE** nas
tabelas oficiais e sem UPDATE no histórico.

## Consequências
- Limites (02/10/2026): 1 GB por projeto, 100 CU-hora/mês, desliga após 5 min sem uso, histórico
  de restauração de só 6 horas, 5 GB/mês de saída de dados.
- Ao "acordar", a primeira consulta é mais lenta. Aceitável.
- 6 horas de histórico não é backup: ver ADR-0007.
- Branches do Neon servem para ambientes de prévia.

## Alternativas consideradas
- **Supabase (grátis):** 500 MB e **pausa o projeto após 7 dias sem uso**, o que é provável na
  fase de obra (pode passar uma semana sem aviso). Também traz auth e API próprias que não
  vamos usar.
- **Postgres no mesmo lugar da API:** a Vercel não oferece Postgres próprio; via marketplace,
  o provedor é o próprio Neon.
