# Spec · M1 · Épico A · Acesso

| | |
|---|---|
| **Marco** | M1 · Acesso e mural (`docs/07-roadmap.md`, seção 4) |
| **Issues** | #2 H-01 · #3 H-02 · #4 H-03 · #5 H-06 · #14 layout e tema · #15 política de privacidade (RNF-11) |
| **Base** | `03-historias.md` (H-01, 02, 03, 06), `02-requisitos.md` (RF-03 a RF-08, RNF-03, 04, 10 a 13), ADR-0005, `04-modelo-de-dados.md` seção 5, contrato `m1-contrato.md` seção 4.2, protótipo |
| **Criado em** | 05/10/2026 |
| **Plano** | `docs/superpowers/plans/m1-acesso.md` |
| **Dúvidas** | `docs/superpowers/duvidas-m1-acesso.md` |

## 1. Objetivo

Implementar as rotas do épico A já descritas no contrato (seção 4.2) e trocar as quatro telas de
marcação de lugar (`/entrar`, `/primeiro-acesso`, `/privacidade`, `/minha-unidade`) pelas telas
de verdade, com os textos e o comportamento do protótipo. Cada critério de aceite vira teste.

Nada de arquivo comum muda. O que precisaria mudar fica como pedido em `duvidas-m1-acesso.md`.

## 2. API

Rotas em `app/rotas/acesso.py` (finas: recebem, chamam o serviço, fazem commit e gravam o
cookie); regras em `app/servicos/acesso.py`. Erros conforme o contrato.

### 2.1 Entrar (H-02, H-03)

**Mudou na revisão do M1 (C2, dúvida 35 de `duvidas-m1.md`):** o bloqueio é por **(login, IP)**,
não da unidade inteira, em `entrada_tentativa` (migração 0003; serviço `app/servicos/tentativas.py`).
O IP vem de `x-real-ip` na Vercel e de `request.client.host` fora dela, e vai ao banco só como
HMAC.

Ordem de decisão, com a linha do par (login, IP) travada (`select … for update`) para duas
tentativas ao mesmo tempo não contarem uma só:

1. Linhas vencidas (`expira_em < now()`) são apagadas.
2. Par bloqueado (`bloqueada_ate > now()`, relógio do banco) → 423 `unidade_bloqueada`, com
   `bloqueada_ate` e `minutos_restantes` (arredondado para cima, mínimo 1). Não confere a senha
   nem conta tentativa nem estende o prazo.
3. Login inexistente ou unidade desativada → `conferir_sem_unidade` (gasta o tempo de um hash) e
   conta como senha errada (a resposta não pode revelar se o apartamento existe).
4. Senha errada → a data entra em `falhas_em`; só contam as dos últimos 15 minutos. A partir do
   **3º** erro a mensagem do 401 diz quantas tentativas faltam (`tentativas_restantes`, U3). No
   **5º** dentro de 15 minutos: `bloqueada_ate = now() + 15 min`, histórico `unidade_bloqueada`
   (sistema: `unidade_id` nulo, entidade `unidade`; nunca o IP) e o próprio 5º já responde 423
   com o horário (antes respondia 401 e só o 6º via o bloqueio).
5. Senha certa → apaga a linha do par (zera aquele login naquele IP), sessão nova, cookie e `Eu`
   (com `precisa_trocar_senha` se for o caso: a tela vai para o primeiro acesso).

O "Apagar meus dados" (2.3) também pede a senha e conta no mesmo contador.

### 2.2 Primeiro acesso (H-01)

Sessão restrita (`SessaoQualquer`). Já concluído → 409 `primeiro_acesso_ja_feito`. Grava
contatos, `precisa_trocar_senha = false`, `ativada_em = now()`, `trocar_senha_e_sessao` (todas as
sessões encerradas, uma nova para quem concluiu), histórico `primeiro_acesso`, cookie novo, `Eu`.

### 2.3 Minha unidade (H-06)

- `GET`: dados, papéis e aparelhos **ainda válidos** (não encerrados, usados nos últimos 180
  dias, abertos depois da última troca de senha), do uso mais recente para o mais antigo;
  `este_aparelho` marca a sessão da requisição.
- `PUT …/dados`: mesmas regras do primeiro acesso. Não vai para o histórico (não é ação de
  gestão nem de segurança; dúvida A4).
- `PUT …/senha`: senha atual errada → 400 `senha_atual_incorreta`. Certa: `trocar_senha_e_sessao`,
  histórico `senha_trocada`, cookie novo (os outros aparelhos caem).
- `DELETE …/aparelhos/{id}`: só sessão em vigor da própria unidade; senão 404
  `aparelho_nao_encontrado`. Histórico `aparelho_desconectado` (entidade `sessao`). Se for o
  próprio aparelho, apaga o cookie.
- `POST …/apagar-dados`: pede `senha` (a atual; revisão do M1, C1). Errada → 400
  `senha_atual_incorreta` (campo `senha`), contando para o bloqueio do (login, IP) como na
  entrada. Papel de gestão em vigor → 409 `unidade_com_papel_de_gestao`. Senão:
  contatos nulos, senha `mudar123`, `precisa_trocar_senha = true`, `ativada_em = null`, as linhas
  de sessão da unidade **apagadas** (a descrição do aparelho é dado pessoal; dúvida A3), histórico
  `dados_apagados`, cookie apagado. Votos e leituras ficam.

## 3. Telas

Todas dentro da casca (`Tela`), sem `style=` (CSP); o pouco CSS próprio vai em
`web/src/acesso/acesso.css`.

| Tela | Conteúdo (do protótipo) |
|---|---|
| `/entrar` | Marca, título, "Os avisos oficiais do condomínio, num lugar só."; bloco em 5 botões de rádio, apartamento só números (até 3; colar `1203` marca o bloco 1 e deixa `203`), senha, "Entrar". Erro 401 e bloqueio 423 numa caixa `role="alert"` em cima do formulário, que recebe o foco. "Esqueci minha senha" abre a resposta do M1 (falar com a administração, H-04 fica para o M2). Link para a política de privacidade. |
| `/primeiro-acesso` | Placa grande, o aviso "Se você não é desta unidade, não continue. A conta é da família que mora ou vai morar aqui.", botão "Não é o meu apartamento, voltar" (sai da sessão), senha nova duas vezes, nome, celular, e-mail marcado como opcional, "Salvar e entrar", e a política de privacidade abrível ali mesmo (sem sair do formulário). Validação na tela com as mesmas mensagens da API; erro da API mostrado no campo certo. Concluído → mural com o recado "Pronto! O apartamento está ativado." |
| `/privacidade` | Pública. Que dados, para quê, quem vê, quando somem, o que não guardamos, direitos do titular (ver, corrigir, apagar em "Minha unidade"). Texto do `04-modelo-de-dados.md`, seção 5, na voz do morador. |
| `/minha-unidade` | Ficha (apartamento, responsável, celular formatado, e-mail ou "não informado", papel), "Mudar meus dados" e "Trocar a senha" (formulários que abrem na própria tela), aparelhos conectados com "Desconectar" (o próprio aparelho aparece como "este aparelho"), "Sair deste aparelho", seção Privacidade com o link da política e "Apagar meus dados" com confirmação em dois passos. |

Acessibilidade (persona Dona Socorro): alvos de 44 px (CSS da casca), rótulo em todo campo,
`aria-describedby` nas ajudas, `aria-invalid` + mensagem ligada ao campo com erro, caixa de erro
com `role="alert"` e foco, botões com estado "Entrando…" desabilitados durante o envio.

## 4. Layout e tema (#14)

Entregues pela casca na onda do contrato. Aqui só se confere no navegador: celular (390 px) e
computador (1366 px), claro e escuro, sem violação de CSP no console (build servido com os
cabeçalhos do `vercel.json`).

## 5. Fora do escopo

Esqueci a senha por e-mail (H-04, M2), instalar/notificações (H-05, M2), limite por IP no
firewall da Vercel (portão do M1, fora do código).
