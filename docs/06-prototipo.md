# 06 · Protótipo de telas — Entrega 1

| | |
|---|---|
| **Status** | v0.1 |
| **Autor** | Erick Santos Dantas |
| **Criado em** | 02/10/2026 |
| **Base** | `03-historias.md` v0.1 |
| **Protótipo** | [`prototipo/index.html`](../prototipo/index.html) |
| **Próximo documento** | `07-roadmap.md` |

---

## 1. Como abrir

O protótipo é **uma página só, clicável**, com dados fictícios. Basta abrir
`prototipo/index.html` no navegador; não precisa instalar nada nem ter internet.

- No computador, aparece dentro de uma moldura de celular. No celular, ocupa a tela toda.
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

Pensadas para a **Dona Socorro** (62 anos, usa pouco além do WhatsApp).

| Decisão | Por quê |
|---|---|
| Texto base de **18 px**, botões com no mínimo **52 px** de altura | Leitura sem óculos e toque sem errar (RNF-02) |
| Uma ação principal por tela, botão verde largo | Não deixar dúvida sobre "o que eu faço aqui" |
| Navegação por **4 abas fixas embaixo** (Avisos, Enquetes, Documentos, Minha unidade) | Padrão dos apps que ela já usa; tudo a 1 toque (RNF-02). O administrador ganha uma 5ª aba. |
| Ícones **sempre com texto** | Ícone sozinho é adivinhação |
| Gestão vê **botões a mais** nas mesmas telas, não um "outro app" | A Carla aprende uma tela só; o botão "＋ Novo aviso" aparece no próprio mural |
| Textos de ajuda embaixo dos campos, em linguagem do dia a dia | "Junte o número do bloco com o do apartamento" em vez de "login" |
| Nada com cara de "apagar" para coisa oficial | Só "Corrigir" e "Arquivar" (RN-05) |
| Contraste AA, foco visível em amarelo ao navegar por teclado | Acessibilidade (RNF-04) |

**Cores:** verde inspirado na identidade do empreendimento, sem usar logotipo nem marca da
construtora. Tokens no início do `<style>` do protótipo (`--verde`, `--verde-escuro`,
`--verde-claro` etc.), que viram os tokens do app real.

## 4. Verificação feita

Em 02/10/2026, o protótipo foi aberto num Chrome automatizado em **27 combinações de tela e
perfil**, sem nenhum erro de JavaScript. Foram testados votar (o placar muda e a troca de voto
desconta o anterior) e publicar aviso (aparece no mural). As telas foram conferidas em print,
também em largura de celular (390 px).

**Não testado ainda:** uso por pessoas reais. O próximo passo natural é mostrar para alguém da
Comissão e para uma pessoa mais velha do grupo, pedindo que façam o primeiro acesso e votem sem
ajuda, e anotar onde travarem.
