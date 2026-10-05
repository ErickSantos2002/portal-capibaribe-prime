# Plano · M1 · Épico C · Avisos (só texto)

Spec: `docs/superpowers/specs/m1-avisos.md`. TDD: cada tarefa começa pelo teste vermelho.
Banco de teste próprio: `PORTAL_TESTE_BANCO=portal_m1_avisos`.

## Tarefas

1. **Esquemas.** `blocos` recusado também quando omitido com `para_todos = false`
   (`validate_default`); `Destinos`/`DestinoBloco` (rota nova) com espelho TS.
   Teste: `test_avisos_esquemas.py`, `test_contrato.py`.
2. **Serviço + rotas de publicar e abrir.** `POST /api/avisos`, `GET /api/avisos/{id}`,
   `GET /api/avisos/alcance`, `GET /api/avisos/destinos`. Teste: `test_avisos_publicar.py`.
3. **Mural e busca.** `GET /api/avisos`, `GET /api/avisos/nao-lidos`, `POST …/lido`.
   Teste: `test_avisos_mural.py`.
4. **Corrigir, arquivar, fixar.** `PUT /api/avisos/{id}`, `POST …/arquivar`, `PUT …/fixado`.
   Teste: `test_avisos_corrigir.py`.
5. **Quem leu.** `GET …/leitura` e `leitura` no aviso. Teste: `test_avisos_leitura.py`.
6. **Permissões.** Toda rota de gestão × comum e sessão restrita; Bloco 2 × aviso do Bloco 1.
   Teste: `test_avisos_permissoes.py`.
7. **Front: texto puro e formatos.** `TextoDoAviso` (parágrafos, quebras, links seguros),
   assinatura ("pela Comissão"), destino. Teste: `texto.test.tsx`, `formatos.test.ts`.
8. **Front: telas.** Mural, arquivados, aviso, novo, corrigir, quem leu. Testes de componente
   com `fetch` falso (`telas.test.tsx`).
9. **Navegador.** Playwright contra API (8103) e Vite (5103) locais: 390 px e 1366 px, claro e
   escuro, sem violação de CSP (`vite preview` com os cabeçalhos do `vercel.json`).
10. **Verificação final.** pytest, pyright, ruff, lint, typecheck, vitest, build.

## Critério de aceite → teste

| História | Critério | Teste |
|---|---|---|
| H-12 | Título, texto e destino (todos ou blocos) | `test_avisos_publicar.py::test_publica_para_todos`, `::test_publica_para_blocos` |
| H-12 | Fixar no topo | `test_avisos_publicar.py::test_publica_fixado` |
| H-12 | Prévia com quantas unidades recebem | `test_avisos_publicar.py::test_alcance_*`; `telas.test.tsx` (prévia antes de publicar) |
| H-12 | "Publicado pela Comissão" e a data | `test_avisos_publicar.py::test_assinatura_*`; `formatos.test.ts` |
| H-14 | Fixados primeiro, depois do mais novo | `test_avisos_mural.py::test_ordem_do_mural` |
| H-14 | Não lido destacado | `test_avisos_mural.py::test_lido_por_unidade`; `telas.test.tsx` ("Novo") |
| H-14 | Busca no título e no texto | `test_avisos_mural.py::test_busca_*` |
| H-14 | Só avisos do bloco da unidade | `test_avisos_mural.py::test_mural_so_do_bloco`, `test_avisos_permissoes.py` |
| H-15 | "Editado em" com versão anterior | `test_avisos_corrigir.py::test_corrigir_cria_versao`; `telas.test.tsx` |
| H-15 | Arquivar tira do mural, fica em arquivados | `test_avisos_corrigir.py::test_arquivar_*` |
| H-15 | Não existe apagar | `test_avisos_corrigir.py::test_nao_existe_rota_de_apagar`; `telas.test.tsx` |
| H-16 | Gestão vê "Lido por X de Y" e quem não leu | `test_avisos_leitura.py` |
| H-16 | Conta como lido ao abrir | `test_avisos_leitura.py::test_abrir_*`; `telas.test.tsx` (POST ao abrir) |
