# ADR-0001 · Stack: React + TypeScript no front, FastAPI + PostgreSQL na API

| | |
|---|---|
| **Status** | Aceita |
| **Data** | 02/10/2026 |

## Contexto
O Portal precisa de web e celular com um código só (PWA), API com regras de permissão e um banco
relacional (o modelo de dados depende de chaves, triggers e permissões). O projeto também é
portfólio de quem trabalha com backend e dados.

## Decisão
- **Front-end:** React + TypeScript, empacotado com Vite, PWA via `vite-plugin-pwa`.
- **API:** Python 3.12, FastAPI, SQLAlchemy 2 (síncrono com `psycopg` 3), Alembic para migrações.
- **Banco:** PostgreSQL.

## Consequências
- É a mesma stack usada no trabalho (H&S): menos coisa nova ao mesmo tempo, e o portfólio mostra
  a stack que o autor domina.
- Duas linguagens no projeto (TypeScript e Python), com dois conjuntos de testes.
- Front e API separados obrigam a escrever o contrato da API, o que é bom: o FastAPI gera o
  OpenAPI sozinho, e os tipos do front podem ser gerados a partir dele.

## Alternativas consideradas
- **Next.js full-stack (só TypeScript):** um projeto só e hospedagem natural na Vercel, mas tira
  o backend Python, que é o foco do portfólio.
- **Django:** traz admin pronto, mas é mais pesado para uma API pequena e foge da stack do trabalho.
