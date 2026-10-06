# Dúvidas e decisões do M1 · Épico A · Acesso

Decisões tomadas sem perguntar a ninguém (mesma regra de `duvidas-m1.md`). **[Erick]** marca o
que só o Erick pode confirmar; o resto é decisão técnica, revisável na revisão do marco.

## Pedidos de mudança no comum

### A1. Dois testes da casca procuram o texto da marcação de lugar (bloqueia o "tudo verde")
- **Problema:** `web/src/rotas.test.tsx` (comum) espera `screen.findByText(/H-02/)` em dois
  testes ("sem sessão, o mural manda para a entrada" e "a entrada não tem topo nem menu…"). O
  texto "H-02" só existia na tela `EmConstrucao`; com a tela de entrar de verdade, os dois falham.
  Nada no épico A pode fazer "H-02" aparecer na tela sem pôr lixo na interface.
- **Pedido:** trocar as duas linhas por
  `await screen.findByRole('heading', { level: 1, name: 'Portal Capibaribe Prime' })`.
  Com isso, `npm test` fica verde (conferido localmente aplicando a troca e desfazendo, sem
  commit).

### A2. A descrição do aparelho fica no banco depois de "Sair"
- **Problema:** o inventário de dados pessoais (`04-modelo-de-dados.md`, seção 5) diz que a
  descrição do aparelho "some ao encerrar a sessão", mas `encerrar_sessao`/`encerrar_todas`
  (comuns) só preenchem `encerrada_em`: a linha, com `aparelho`, fica para sempre.
- **O que fiz no épico:** "Apagar meus dados" **apaga** as linhas de sessão da unidade (o `app`
  tem DELETE em `sessao`; nada referencia `sessao` por chave estrangeira).
- **Pedido:** decidir entre apagar a linha ao sair/desconectar, limpar `aparelho` ao encerrar,
  ou uma limpeza periódica das encerradas; ou corrigir o inventário.

## Decisões do épico

### A3. O bloqueio responde 423 a partir da 6ª tentativa
- **Revista na revisão do marco:** o bloqueio passou a ser por (login, IP), o 5º erro já
  responde 423 e login inexistente conta. Ver a dúvida 35 de `duvidas-m1.md`.
- **Dúvida:** o contrato diz "5 erros seguidos: `bloqueada_ate = now() + 15 min`"; H-03 diz
  "5 tentativas erradas, quando vier a 6ª, fica bloqueado".
- **Decisão:** a 5ª errada grava o bloqueio e ainda responde 401 `credenciais_invalidas`; a 6ª
  (mesmo com a senha certa) recebe 423. Tentativa durante o bloqueio não confere a senha, não
  conta nem estende o prazo. Login inexistente nunca conta (não há linha para travar).
- **Por quê:** é a leitura literal do critério de aceite; não muda segurança (o bloqueio já está
  gravado na 5ª).

### A4. "Mudar meus dados" não vai para o histórico
- **Decisão:** não registra nada (não há `Acao` para isso, e `historico` é comum).
- **Por quê:** RNF-14 pede registro de ações de **gestão**; trocar o próprio celular não é. Se o
  Erick quiser ver "conta tomada" pelo histórico, valeria uma ação `dados_alterados` (pedido no
  comum). **[Erick]** só se quiser.

### A5. Senha atual errada em "Trocar a senha" não conta para o bloqueio
- **Por quê:** quem chega ali já tem sessão aberta na unidade; o bloqueio de H-03 protege a
  entrada. Contar complicaria (bloquear a entrada de quem já está dentro).

### A6. "Só a administração do Portal vê" o celular (não "só a Comissão")
- **Dúvida:** o protótipo diz "Só a Comissão vê" na ajuda do celular; a dúvida 9 do M1 deixou o
  painel com os contatos só para o admin.
- **Decisão:** o texto diz o que é verdade hoje: "Só a administração do Portal vê". A política
  de privacidade diz o mesmo ("o próprio apartamento e a administração do Portal").
- **[Erick]** se a Comissão passar a ver os contatos (dúvida 9), mudar os dois textos juntos.

### A7. Texto da política de privacidade
- **Decisão:** escrito a partir do inventário (`04-modelo-de-dados.md`, seção 5), na voz do
  morador: o que guardamos e para quê, quem vê, o que não guardamos, por quanto tempo, direitos.
  Fica em `web/src/acesso/Privacidade.tsx` e aparece em `/privacidade` (pública, linkada na
  entrada) e dobrada dentro do primeiro acesso (lida sem perder o que já foi digitado).
- **[Erick]** conferir antes de abrir para o grupo: (1) quem é o "controlador" dos dados (o texto
  diz só "a administração do Portal", sem nome nem CNPJ do condomínio); (2) se quer citar onde
  ficam os dados (Neon/Vercel, região); (3) o e-mail é descrito como "quando essas funções
  chegarem" (M2).

### A8. Apartamento que não pode existir: a mesma mensagem, sem chamar a API
- **Decisão:** Bloco 3 + "999" (andar 9) mostra "Bloco, apartamento ou senha incorretos." na
  própria tela. A API responderia 422 com "Escolha o bloco e escreva o número do apartamento.",
  que confunde quem escolheu e escreveu.
- **Por quê:** igual ao protótipo; o formato é público, não revela nada.

### A9. Esqueci a senha (H-04 fica para o M2)
- **Decisão:** "Esqueci minha senha" na entrada abre (sem sair da tela) a resposta que o roadmap
  prevê para o M1: falar com a administração no grupo do WhatsApp, que reseta a senha (H-08).

### A10. Depois de entrar, volta para o link aberto
- **Decisão:** quem abriu um link (ex.: `/avisos/12` colado no grupo) sem sessão volta a ele
  depois de entrar (a casca já guarda `state.de`). Primeiro acesso sempre vai para o mural.

### A11. Navegar e mudar a sessão na mesma transição
- **Problema achado nos testes:** `definir(eu)` seguido de `navigate(...)` deixava a guarda da
  rota navegar primeiro (o React Router 8 navega dentro de `startTransition`) e o recado
  ("Pronto! O apartamento está ativado.", "Seus dados foram apagados.") se perdia.
- **Decisão:** as telas do épico fazem as duas coisas dentro de um mesmo `startTransition`.
  **Aviso aos outros épicos** que mexerem na sessão e navegarem com recado.

### A12. Erro no formulário: caixa em cima e mensagem no campo
- **Decisão:** além da caixa com `role="alert"` (como no protótipo), o campo com problema ganha
  borda vermelha, `aria-invalid`, a mensagem logo abaixo (ligada por `aria-describedby`) e o
  foco. A mensagem aparece duas vezes na tela; para a Dona Socorro, ver o erro colado no campo
  vale a repetição.

### A13. Teste de CSRF por rota
- **Decisão:** `test_acesso_csrf.py` lista à mão as 6 rotas do épico que alteram dados, confere a
  lista contra `app.openapi()["paths"]` (aviso do épico B: `app.routes` não enxerga roteadores
  incluídos no FastAPI 0.142) e prova o 403 sem `X-Portal` em cada uma. Mutação conferida: sem a
  dependência no roteador, 6 testes falham.

### A14. Teste no navegador fora do MCP compartilhado
- **Observação:** o navegador do MCP playwright é compartilhado entre os agentes (a aba trocou
  para a porta de outro épico no meio do teste). Os testes de navegador do épico A rodaram num
  script Playwright com contexto próprio (Chrome headless), contra o build servido com os
  cabeçalhos de produção (`vite preview`), API em 8101 e banco `portal_m1_acesso_dev`.
  Resultado: nenhuma violação de CSP; único aviso é o `bluetooth` do `Permissions-Policy`
  (dúvida 26 do M1).
