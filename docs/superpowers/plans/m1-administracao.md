# Plano · M1 · Épico B · Administração

Spec: `docs/superpowers/specs/m1-administracao.md`. Branch `m1/administracao`. Banco de teste
`PORTAL_TESTE_BANCO=portal_m1_administracao`. Cada tarefa: teste falhando → código mínimo →
verde → commit.

## Tarefas

1. **Portão de permissão** (`test_administracao_permissoes.py`): descobre as rotas `/api/admin`
   em `app.routes`; para cada uma, conta comum (403 `sem_permissao`), Comissão (403), sessão
   restrita de 4203 (403 `primeiro_acesso_pendente`), sem sessão (401) e alteração sem `X-Portal`
   (403 `requisicao_recusada`); confere que `historico`, `unidade_papel` e `unidade` não mudaram.
   Falha enquanto as rotas não existem (o teste também exige as 6 rotas do contrato).
2. **Painel (H-07)** (`test_administracao_painel.py`): 320 unidades por bloco com os campos;
   resumo geral e por bloco; os três filtros; unidade desativada fora; 422 em filtro inválido;
   `no-store`.
3. **Ficha** (`test_administracao_unidade.py`): campos, aparelhos válidos, 404 (inexistente,
   fora do padrão, desativada).
4. **Reset (H-08)** (`test_administracao_reset.py`): estado inicial completo; senha `mudar123`
   entra e a antiga não; sessões derrubadas (cliente logado recebe 401); papel retirado com
   `retirado_por`; leituras de aviso ficam; histórico `unidade_resetada` + `papel_retirado`;
   422 sem `confirmo`; 409 `ultimo_admin` sem mudar nada; 404.
5. **Papéis (H-09)** (`test_administracao_papeis.py`): conceder → Comissão vê gestão em
   `/api/acesso/eu`; retirar → some na próxima requisição da mesma sessão; idempotência sem
   histórico duplicado; 409 `unidade_nao_ativada`; 409 `ultimo_admin`; dar admin a outra e então
   retirar o próprio; 422 papel inválido; histórico de cada mudança.
6. **Histórico (H-11)** (`test_administracao_historico.py`): mais novo primeiro, quem fez,
   ação, item afetado (`unidade_afetada`, `aviso_titulo`), "Portal" para ação do sistema,
   paginação com `proximo`, limites 422, sem dado pessoal na resposta; `app` não apaga (já
   coberto em `test_permissoes.py`, citado).
7. **Contrato**: `unidade_afetada` e `aviso_titulo` no esquema e no TS; `test_contrato.py` verde.
8. **Front**: `Painel.tsx`, `FichaUnidade.tsx`, `Historico.tsx`, `frases.ts` (texto de cada
   ação), `administracao.css`; testes vitest das três telas e das frases em
   `administracao.test.tsx`; rotas trocam `EmConstrucao`.
9. **Navegador**: Playwright em 390/1366, claro/escuro, console sem CSP; prints em
   `docs/superpowers/prints/m1-administracao/`.
10. **Fechamento**: pytest inteiro, pyright, ruff, lint, typecheck, test, build; dúvidas.

## Critério de aceite → teste

| Critério | Teste |
|---|---|
| H-07 lista as 320 unidades por bloco, com ativada, data, responsável, celular | `test_painel_lista_as_320_unidades_por_bloco_com_os_dados` |
| H-07 total e percentual, geral e por bloco | `test_painel_resume_adesao_geral_e_por_bloco` |
| H-07 filtros ativadas / não ativadas / gestão | `test_painel_filtra` (parametrizado) + `test_painel_filtra_nao_ativadas` |
| H-08 pede confirmação mostrando o que vai acontecer | `test_resetar_sem_confirmar_recusa` + `administracao.test.tsx` "pede confirmação mostrando o que vai acontecer" |
| H-08 senha `mudar123`, contatos, aparelhos, papel, "não ativada" | `test_resetar_volta_a_unidade_ao_estado_inicial`, `test_resetar_desconecta_todos_os_aparelhos`, `test_resetar_retira_os_papeis` |
| H-08 votos continuam valendo (no M1: leituras) | `test_resetar_mantem_as_leituras` |
| H-08 registrado no histórico | `test_resetar_registra_no_historico` |
| H-09 dar Comissão → opções aparecem | `test_dar_comissao_libera_a_gestao` |
| H-09 retirar → somem na hora, mesmo logada | `test_retirar_comissao_vale_na_hora_mesmo_logada` |
| H-09 último admin não sai | `test_nao_retira_o_ultimo_admin`, `test_resetar_o_ultimo_admin_recusa` |
| H-09 concessão e retirada no histórico | `test_papeis_registram_no_historico` |
| H-11 registra as ações (as do M1) | `test_historico_mostra_as_acoes_do_m1` |
| H-11 data/hora, unidade que fez, ação, item afetado | `test_historico_traz_quem_quando_o_que_e_o_item` |
| H-11 só o admin vê | `test_administracao_permissoes.py` (todas as rotas) |
| H-11 ninguém apaga | `test_historico_nao_tem_rota_de_apagar` + `test_permissoes.py::test_app_nao_altera_historico` |
| RNF-13 toda rota de gestão recusa conta comum | `test_toda_rota_admin_recusa` (parametrizado por rota × perfil) |
