# M2 · Ajustes depois da 1.2.0 · Plano de implementação

> **Para agentes:** executar tarefa por tarefa, com TDD (`superpowers:test-driven-development`).
> Passos em checkbox (`- [ ]`).

**Objetivo:** as duas respostas do Erick que mudam o Portal (`duvidas-m2.md`, "Respostas do
Erick"): quem publica também recebe o aviso, e a opção "Receber os avisos por e-mail" em Minha
unidade. Saem juntas na **versão 1.3.0** (novidade visível: minor).

**Base:** `duvidas-m2.md` (itens 4 e 7 e as respostas), `duvidas-m2-email.md` (item 3),
`specs/m2-contrato.md` (seções 2 e 5), `specs/m2-email.md` (2.2), `specs/m2-push.md`.

## Restrições globais

- `uv run --frozen`; banco de teste próprio (`PORTAL_TESTE_BANCO=portal_teste_ajustes`, num
  Postgres 17 local). Nada no Neon: a 0006 roda lá pelas mãos do coordenador, antes do push.
- Commits pequenos na branch `m2/ajustes`, em português, com `Co-Authored-By`. Sem merge, sem push.
- Correção de aviso continua **sem** notificar (resposta ao item 6): nada muda ali.

## Decisões de desenho

- **Coluna** `unidade.receber_avisos_email boolean not null default true` (migração 0006). No
  modelo, `server_default=true()` e o atributo nunca vai como `None` num INSERT (o gotcha do
  SQLAlchemy: NULL explícito desliga o DEFAULT). As 320 unidades que já existem ficam ligadas.
- **API:** `GET /api/minha-unidade` ganha `receber_avisos_email: bool`. Alterar é
  `PUT /api/minha-unidade/avisos-por-email` com `{"receber": true|false}` (exige `X-Portal: 1`,
  como as outras), que devolve `MinhaUnidade`. Aceita mesmo sem e-mail cadastrado (é só a
  preferência; a tela nem mostra a opção sem e-mail).
- **Destinos:** `_unidades_do_destino` perde o `Unidade.id != publicado_por` (vale para push e
  e-mail, e para os outros aparelhos da unidade de quem publicou); `destinos_email` ganha
  `Unidade.receber_avisos_email`. A recuperação de senha não olha a opção.
- **"Apagar meus dados"** volta a opção para ligada: o apartamento recomeça do zero, e o próximo
  responsável decide por si.
- **Rodapé do e-mail do aviso:** "Para não receber mais, desligue “Receber os avisos por e-mail”
  em Minha unidade." (substitui a frase de apagar o e-mail e o alerta do item 3 de
  `duvidas-m2-email.md`).
- **Tela:** dentro da seção "Notificações" de Minha unidade, um cartão "Por e-mail" com a caixa de
  marcar "Receber os avisos por e-mail" (estilo `.opcao`, alvo grande) que salva na hora; sem
  e-mail cadastrado, só a frase que explica como cadastrar.
- **Backup:** `verificacoes.sql` confere tabelas, não colunas; só o comentário "até a 0005" muda.

## Tarefas

- [x] **1. Quem publica também recebe.** Testes: `test_push_para_todos_menos_quem_publicou` vira
  "quem publicou também recebe, nos dois aparelhos"; teste novo de e-mail para quem publicou.
  Depois: tirar a exclusão; docstrings.
- [x] **2. Migração 0006 + modelo.** Testes: coluna existe, NOT NULL, padrão `true` para as
  unidades que já existiam e para INSERT novo pelo ORM; downgrade volta à 0005; modelos iguais
  ao banco (`test_modelos.py`, já existente). Depois: `0006_receber_avisos_email.py` e o modelo.
- [x] **3. API da opção.** Testes: GET traz `receber_avisos_email: true`; PUT liga/desliga e
  devolve a unidade; PUT sem `X-Portal` → 403 (`test_acesso_csrf.py`); sem sessão → 401; corpo
  sem booleano → 422; apagar dados volta para `true`. Esquemas e `tipos.ts` (`test_contrato.py`).
- [x] **4. Destinos e rodapé.** Testes: `destinos_email` pula quem desligou; push continua
  chegando para quem desligou o e-mail; recuperação de senha funciona com a opção desligada;
  rodapé novo no texto e no HTML.
- [x] **5. Tela.** Testes (Vitest): a caixa aparece marcada, desmarcar chama a API e mostra o
  recado; sem e-mail, a frase de cadastrar; erro da API aparece. Depois: componente, CSS.
- [x] **6. Versão 1.3.0 + novidades** no mesmo commit da tela.
- [x] **7. Docs:** `m2-contrato.md` (2, 5), `m2-email.md` (2.2), `m2-push.md` se citar,
  `04-modelo-de-dados.md` (coluna nova), comentário do `verificacoes.sql`, registro no fim de
  `duvidas-m2.md`.
- [x] **8. Conferência visual** (uvicorn + vite preview + Playwright): 1 ou 2 prints em
  `docs/superpowers/prints/m2-ajustes/`.
- [x] **9. Suíte inteira** (pytest, vitest, eslint, tsc, ruff, pre-commit) antes de cada commit.
