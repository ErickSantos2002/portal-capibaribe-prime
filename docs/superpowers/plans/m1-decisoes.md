# Plano · M1 · Decisões do fim do marco

| | |
|---|---|
| **Branch** | `m1/decisoes` |
| **Base** | `main` depois da revisão do M1 (#19) |
| **Dúvidas** | `docs/superpowers/duvidas-m1.md`, seção "Fim do marco" |

Decisões do Erick e do coordenador em 06/10/2026. Cada item ganha antes um teste que falha na
`main` (TDD). Sem migração nova.

| # | Item | Teste que falha antes |
|---|---|---|
| 1 | Gestão lê o painel e a ficha (`exige_gestao`); reset, papéis e histórico continuam do admin | `api/testes/test_administracao_permissoes.py` (leitura pela Comissão, recusa do resto, conjunto de rotas de leitura) |
| 1 | Tela: "Unidades" no menu da Comissão; painel sem o link do histórico; ficha sem as ações | `web/src/rotas.test.tsx`, `web/src/administracao/administracao.test.tsx` |
| 2 | A6: ajuda do celular e "Quem vê" dizem Comissão e administração | `web/src/acesso/MinhaUnidade.test.tsx`, `web/src/acesso/Privacidade.test.tsx` |
| 3 | A7: responsável pelos dados, contato para pedidos e onde os dados ficam | `web/src/acesso/Privacidade.test.tsx` |
| 4 | Admin 5: confirmação ao dar e tirar Comissão | `web/src/administracao/administracao.test.tsx` |
| 5 | Avisos 13: "Para a gestão" | `web/src/avisos/*.test.tsx` |
| 6 | Registro das decisões | — (documento) |

## Passos

1. API: teste de permissões novo → `Gestao` nas duas rotas de leitura → docs (spec, contrato,
   histórias).
2. Front: testes (menu, rotas, ficha da Comissão, painel sem histórico) → guardas, menu, ficha.
3. Confirmação da Comissão: teste → `Confirmacao` com os dois casos novos.
4. Textos A6/A7 e "Para a gestão": testes → textos.
5. Dúvidas: seção "Fim do marco".
6. Navegador (Playwright próprio, banco `portal_m1_decisoes`, API 8130, front 5130): 320/390/1366,
   claro e escuro, CSP, rolagem horizontal, axe. Prints em `docs/superpowers/prints/m1-decisoes/`.
7. Verificação inteira: pytest, pyright, ruff, lint, typecheck, vitest, build.
