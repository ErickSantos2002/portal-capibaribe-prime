# 06 · Protótipo de telas — Entrega 1

| | |
|---|---|
| **Status** | v0.2 — refeito com as skills de design; versão para computador e tema escuro |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 02/10/2026 |
| **Base** | `03-historias.md` v0.1 |
| **Protótipo** | [`prototipo/index.html`](../prototipo/index.html) |
| **Próximo documento** | `07-roadmap.md` |

---

## 1. Como abrir

O protótipo é **uma página só, clicável**, com dados fictícios. Basta abrir
`prototipo/index.html` no navegador; não precisa instalar nada nem ter internet.

- Na barra escura, **Tela** alterna entre celular e computador, e **Tema** entre claro e escuro.
- A barra escura no topo **não faz parte do app**: serve para trocar de perfil (Dona Socorro,
  Rafael, Carla da Comissão, Erick administrador) e pular direto para qualquer tela.
- Nada é salvo. Votar e publicar funcionam até recarregar a página.

Ele serve para **ver e testar o fluxo antes de programar**, inclusive mostrando para a Comissão
no celular. Não é o código do app: a implementação começa do zero, em React (ADR-0001).

## 2. Telas

| Tela | Histórias | Observação |
|---|---|---|
| Entrar | H-02, H-03 | Explica o padrão do login na própria tela. **Não mostra `mudar123`**: a senha só circula no grupo. |
| Entrar · senha errada / bloqueio | H-02, H-03 | Mesma mensagem para login ou senha errados |
| Esqueci minha senha | H-04 | Resposta igual com ou sem e-mail cadastrado |
| Primeiro acesso | H-01 | Alerta "esta é a unidade X, se não for sua, não continue" no topo |
| Instalar e notificações | H-05 | Passo a passo separado para Android e iPhone |
| Documentos públicos | H-18 | Acessível sem entrar |
| Mural de avisos | H-13, H-14 | Fixado no topo, "Novo" com barra azul, busca, ponto azul na aba |
| Aviso | H-14, H-15, H-16 | "Editado em" com versão anterior; gestão vê "Lido por X de Y" |
| Quem leu | H-16 | Lista das unidades que não leram |
| Enquetes / votar / resultado | H-21, H-22 | Voto da unidade, troca de voto, "consulta sem valor legal" |
| Documentos | H-18, H-19 | Por categoria; "Só gestão" só aparece para a gestão |
| Minha unidade | H-05, H-06 | Dados, aparelhos conectados, sair, apagar dados |
| Novo aviso | H-12 | Destino em botões (Todos / Bloco 1…5) e contagem de quantas unidades recebem |
| Nova enquete | H-20 | Aviso de que não dá para editar depois do 1º voto |
| Novo documento | H-17 | Nível de acesso e aviso automático |
| Painel de ativação | H-07, H-10 | Grade de 64 apartamentos por bloco: verde = ativada, contorno amarelo = gestão |
| Unidade (admin) | H-08, H-09 | Resetar e dar/retirar papel; admin único não pode perder o papel |
| Histórico | H-11 | Só leitura |

## 3. Decisões de interface

Versão 0.2, refeita com as skills **frontend-design** (Anthropic) e **ui-ux-pro-max**: sistema de
design gerado pela base do ui-ux-pro-max, plano revisado contra o briefing antes do código, e
crítica por print no final.

### 3.1 Direção

| | |
|---|---|
| **Assunto** | O mural oficial de um condomínio em obra na Várzea, à beira do Capibaribe, num empreendimento chamado "Reserva". |
| **Público** | Compradores de todas as idades; a referência é a Dona Socorro (62 anos, usa pouco além do WhatsApp). |
| **Trabalho principal** | Ler o aviso oficial, votar pela unidade, achar o documento. |
| **Elemento-assinatura** | A **placa do apartamento** (Bloco 1 / 101, como a plaquinha da porta). Aparece no topo, no primeiro acesso e no menu, e ensina o login sozinha: bloco + apartamento. É o único lugar com ousadia; o resto é calmo. |

### 3.2 Tokens

| Token | Claro | Escuro | Papel |
|---|---|---|---|
| `--mata` | `#1f5e3b` | `#7fc79a` | Cor principal: a reserva verde |
| `--ipe` | `#e8b22a` | `#f0c14b` | Destaque: os ipês-amarelos do empreendimento. Só em fixado e marcação de gestão |
| `--ipe-forte` | `#9a6a00` | `#f0c14b` | Contorno de foco e marcações sobre fundo claro |
| `--papel` | `#f4f6f2` | `#101713` | Fundo, com leve tom verde (evita o creme genérico) |
| `--folha` | `#ffffff` | `#18221c` | Superfícies |
| `--tinta` / `--tinta-suave` | `#17231c` / `#4a5a50` | `#e8efe9` / `#a9b8ae` | Texto |
| `--erro` | `#a3322a` | `#f19a90` | Erros e ações destrutivas |

**Fonte:** Atkinson Hyperlegible, criada pelo Braille Institute para baixa visão (recomendação do
ui-ux-pro-max). O zero cortado (Ø) é proposital: separa 0 de O. No app real a fonte é servida
pelo próprio Portal, sem requisição ao Google (LGPD).

**Ícones:** SVG de traço único (2 px), sempre ao lado de texto. Nada de emoji.

### 3.3 Regras de tela

| Decisão | Por quê |
|---|---|
| Texto base 18 px; botões e campos com no mínimo 54 px de altura; alvos de toque ≥ 44 px | Leitura sem óculos e toque sem errar (RNF-02) |
| **Celular:** 4 abas fixas embaixo. **Computador (≥ 900 px):** menu lateral verde com a placa no rodapé e conteúdo numa coluna de até 720 px | Padrão que cada um já conhece no seu aparelho; linha de leitura curta no monitor |
| Mural como **uma folha contínua**, com só o aviso fixado em destaque amarelo | Hierarquia clara; evita a grade de cartões iguais |
| "Novo" sempre escrito, não só uma bolinha de cor | Não depender só de cor |
| Gestão vê **botões a mais** nas mesmas telas | A Comissão aprende uma tela só |
| Textos na voz do morador ("Bloco e apartamento", "Salvar e entrar", "Corrigir aviso") | Nada de "login", "submeter", "editar registro" |
| Nada de "apagar" em coisa oficial: só "Corrigir" e "Arquivar" | RN-05 |
| Tema claro e escuro pelos mesmos tokens | Muita gente usa o celular no escuro sem saber |
| Movimento só em resposta a um toque (recado de confirmação) e desligado em "reduzir movimento" | Calma; acessibilidade |

### 3.4 Contraste medido (WCAG 2.1)

| Par | Claro | Escuro |
|---|---|---|
| Texto sobre fundo | 14,9 : 1 | 15,6 : 1 |
| Texto suave sobre fundo | 6,7 : 1 | 7,9 : 1 |
| Verde (link, botão) sobre fundo | 7,1 : 1 | 9,1 : 1 |
| Texto do botão sobre verde | 7,7 : 1 | 9,0 : 1 |
| Texto sobre o amarelo do fixado | 14,3 : 1 | 10,9 : 1 |
| Erro sobre fundo de erro | 5,6 : 1 | 7,1 : 1 |
| Contorno de foco sobre fundo | 4,35 : 1 | 10,8 : 1 |

Todos acima de 4,5 : 1 para texto e 3 : 1 para elementos que não são texto. A medição pegou um
erro da primeira versão: o foco em `--ipe` dava só 1,78 : 1 no tema claro, por isso nasceu o
`--ipe-forte`.

## 4. Verificação feita

Em 02/10/2026, num Chrome automatizado: **37 combinações** de tela × perfil × celular/computador
× claro/escuro, **sem nenhum erro de JavaScript** e sem rolagem horizontal no computador. Votar
(o placar muda e a troca desconta o voto anterior) e publicar aviso (aparece no mural)
funcionam. Telas conferidas em print.

**Não testado ainda:** uso por pessoas reais, leitor de tela de verdade (TalkBack/VoiceOver) e
fonte ampliada pelo sistema. O próximo passo natural é pedir a alguém da Comissão e a uma
pessoa mais velha do grupo que façam o primeiro acesso e votem sem ajuda, e anotar onde travarem.
