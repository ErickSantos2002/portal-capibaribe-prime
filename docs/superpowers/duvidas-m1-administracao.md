# Dúvidas e decisões do M1 · Épico B · Administração

Decisões tomadas sem perguntar a ninguém, como manda o fluxo dos épicos. **[Erick]** marca o que
só o Erick decide; o resto é técnico e pode ser revisto na revisão do marco.

## 1. Mudança no contrato do épico: o item afetado no histórico
- **Dúvida:** H-11 pede "o item afetado"; `ItemHistorico` só tinha `entidade_id`, um número
  interno que a tela não sabe transformar em "Bloco 1, 106" nem no título do aviso.
- **Decisão:** dois campos novos em `ItemHistorico` (Python e TS juntos, `test_contrato.py`
  verde): `unidade_afetada` (`UnidadeRef`, quando `entidade = "unidade"`) e `aviso_titulo` (título
  da versão em vigor, quando `entidade = "aviso"`).
- **Por quê:** é o que o protótipo mostra ("resetou o Bloco 1, 106", "publicou o aviso “…”").
  Título de aviso não é dado pessoal. O épico B só **lê** `aviso_versao`; nada do épico C muda.
  Para o épico C: o histórico espera `entidade = "aviso"` e `entidade_id = aviso.id`.

## 2. Rotas descobertas pelo `openapi()`, não por `app.routes`
- **Achado:** no FastAPI 0.142 (o do `uv.lock`), `app.routes` guarda cada roteador incluído como
  um objeto interno (`_IncludedRouter`) sem o caminho das rotas. Um teste que percorresse
  `app.routes` procurando `APIRoute` acharia **zero** rotas e passaria sem testar nada.
- **Decisão:** o portão (`test_administracao_permissoes.py`) lista as rotas por
  `app.openapi()["paths"]`, exige as 6 do contrato e confere que o roteador do épico não tem rota
  fora do schema. Conferido por mutação: trocar `Admin` por `Gestao` no histórico derruba o teste.
- **Para os épicos A e C e para o coordenador:** se algum teste comum ou de outro épico percorre
  `app.routes`, ele pode estar vazio sem avisar. Vale conferir.

## 3. Reset também em unidade não ativada
- **Decisão:** a rota aceita resetar qualquer unidade ativa, ativada ou não.
- **Por quê:** a unidade não ativada pode estar bloqueada por senhas erradas (H-03) ou ter alguém
  entrado com `mudar123` e parado no primeiro acesso; o reset tira o bloqueio e derruba essas
  sessões. Nada de dado pessoal é tocado (ela não tem).

## 4. O admin pode resetar a própria unidade ou tirar o próprio papel, se houver outro admin
- **Decisão:** permitido; o banco só impede ficar sem admin (409 `ultimo_admin`). A tela avisa na
  confirmação ("É o seu apartamento: você sai do Portal neste aparelho") e, depois, relê a sessão
  para as guardas levarem a pessoa à tela certa.
- **Por quê:** é o caminho para passar a administração a outra unidade (ex.: o Erick muda de
  apartamento). Proibir obrigaria a pedir a outro admin.

## 5. Confirmação: reset e administrador sim, Comissão não
- **Decisão:** resetar, dar e tirar o papel de **administrador** pedem confirmação no lugar
  (padrão do protótipo), listando o que acontece. Dar e tirar **Comissão** é direto, com recado,
  como no protótipo.
- **Por quê:** H-08 pede confirmação para o reset; administrador dá acesso a contatos e ao poder
  de resetar e tirar papéis de qualquer um, então também é ação de risco. Comissão se desfaz com um
  toque e fica no histórico. **[Erick]** se quiser confirmação também na Comissão, é uma linha.

## 6. Dar o papel de administrador pela tela
- **Dúvida:** H-09 fala só de Comissão; o contrato já aceita `admin` em `PUT …/papeis/{papel}`.
- **Decisão:** a tela oferece "Dar papel de administrador" (com confirmação), porque sem isso a
  trava do último admin não teria saída pela tela, e o spec do contrato (seção 2.5, passo 4) prevê
  "outros admins pela tela de administração (H-09)". **[Erick]** confirmar que quer esse botão
  visível; tirar é esconder um botão.

## 7. Painel: grade e lista
- **Dúvida:** H-07 pede "lista das 320 unidades com responsável e celular"; o protótipo mostra só
  a grade (sem nomes), e 320 linhas com nome no celular é muito para o dia a dia.
- **Decisão:** a grade do protótipo é o padrão (adesão de relance, toque abre a ficha); "Lista com
  contatos" mostra a lista com responsável, celular e data do primeiro acesso, e é nela que valem
  os filtros (Todas, Já entraram, Ainda não, Com papel), usando o `?situacao=` da API. O resumo por
  bloco aparece nos dois.
- **Por quê:** cumpre o critério sem trocar o visual aprovado no protótipo.

## 8. "Único administrador" na ficha
- **Dúvida:** o protótipo mostra "Único administrador. Esse papel não pode ser tirado daqui." na
  ficha do admin. `UnidadeAdmin` não diz quantos admins existem.
- **Decisão:** não mudei o contrato para isso. O botão "Tirar papel de administrador" aparece, e
  a recusa do servidor (409 com a mesma explicação) aparece na hora, numa caixa de erro.
- **Por quê:** a regra é do banco; repetir a contagem na tela daria duas fontes de verdade.

## 9. Votos no reset
- **Dúvida:** H-08 diz "votos já dados continuam valendo"; enquetes só existem no M2+.
- **Decisão:** o teste equivalente do M1 prova que as **leituras de aviso** da unidade ficam
  depois do reset (`test_resetar_mantem_as_leituras`). Quando houver `voto`, vale um teste igual.

## 10. Celular na ficha vira link de ligação
- **Decisão:** `tel:+55<dígitos>`, para o admin ligar em caso de conta tomada (o motivo do RF-06).
  No painel (lista), o celular é só texto, porque a linha inteira já é um link para a ficha.

## 11. Respostas sem cache
- **Decisão:** painel, ficha, ações e histórico respondem `Cache-Control: no-store`.
- **Por quê:** têm nome e celular (LGPD) e dados de segurança; não devem ficar em cache de
  navegador ou de proxy.

## 12. Teste no navegador sem a rota de entrar
- **Observação:** a rota de entrar é do épico A e não está nesta branch. Para o Playwright, a
  sessão do admin fictício foi criada direto no banco local (`criar_sessao`), e o cookie
  `__Host-sessao` posto no navegador. Rodou no build de produção (`vite preview`, com a CSP do
  `vercel.json`) por uma configuração temporária, apagada depois (o `vite.config.ts` é comum e
  aponta para a porta 8000). Console: nenhuma violação de CSP; só o 404 de
  `/api/avisos/nao-lidos` (épico C, esperado pela dúvida 22 do M1) e o aviso conhecido do
  `bluetooth` na `Permissions-Policy` (dúvida 26 do M1).

## Pedidos de mudança no comum

Nenhum obrigatório. Observações para o coordenador:

- **`npm test` depende do build:** a parte `node --test testes/**` lê `web/dist`; numa cópia
  limpa, `npm test` antes de `npm run build` dá 4 falhas. Talvez valha `pretest` ou ordem fixa no
  CI (`package.json` é comum, não mexi).
- **`app.routes` no FastAPI 0.142:** ver item 2.
