# Dúvidas e decisões · logo, ícone e versão

Plano em `plans/logo-versao.md`. Decisões tomadas sem perguntar, registradas para o Erick conferir.

## Imagens

- **Fonte usada: o JPG com fundo branco, não o PNG "sem fundo".** O recorte do PNG deixou o
  contorno com alfa parcial e a cor escurecida: sobre fundo escuro, "CAPIBARIBE" e "prime"
  ficavam sujos e meio apagados. O script tira o branco do JPG ("cor para alfa", como no GIMP),
  o que dá alfa limpo sobre qualquer fundo. Os dois originais seguem fora do repositório.
- **Tamanhos gerados:** `logo.webp` 260×185 (23 KB), `logo@2x.webp` 520×369 (57 KB),
  `favicon.ico` 16/32/48 (3,7 KB), `apple-touch-icon.png` 180 (8,7 KB), `icon-192.png`
  (8,8 KB), `icon-512.png` (37 KB). Refazer: `scripts/dev/gerar-icones.py <logo.jpg>`.
- **Ícones de tela inicial sobre `--papel` (#f4f6f2)**, não branco puro: é o fundo do Portal. A
  espiral ocupa 76% (Apple) e 72% (192/512), dentro da área segura do ícone "maskable" do
  Android, para servirem no PWA sem refazer.
- **Na espiral pequena (16 px) o desenho é fino**: reconhecível como a espiral colorida, não
  como detalhe. Um ícone desenhado à mão para 16 px seria o caminho se incomodar.
- **O `favicon.svg` antigo (a placa verde) saiu.** Navegadores preferem o SVG quando os dois
  existem, e ele não tem mais nada a ver com a marca.

## Manifest do PWA: ficou para o M2

Declarar um `manifest.webmanifest` não pede service worker nem mexe na CSP (`manifest-src` cai
no `default-src 'self'`). Mas ele muda comportamento: o Chrome passa a oferecer "Instalar app",
e `display`, `start_url` e `scope` são decisões do M2 (notificações), que é onde o PWA nasce. Os
ícones 192 e 512 já estão em `web/public/`, prontos.

## Janela de versão

- **`<dialog>` nativo com `showModal()`** (o app não tinha componente de janela). O nativo já
  deixa o resto da tela inerte e fecha com Esc. Mesmo assim o Tab passava pela barra do
  navegador antes de voltar (foco no `body`); acrescentei o ciclo explícito do último para o
  primeiro elemento, para ficar preso de verdade.
- **A janela só existe no DOM enquanto aberta**: nunca duas ao mesmo tempo (Minha unidade tem
  dois botões no DOM, um escondido por CSS conforme a largura).
- **Clicar no fundo escurecido também fecha.** Não estava pedido; é o esperado de uma janela que
  só informa (não há nada a perder).
- **O primeiro foco cai na área de rolagem "O que mudou"** (focável, para o teclado rolar no
  celular; o axe exige isso de área rolável). O leitor de tela anuncia "Versão 1.1.0, diálogo"
  e depois a região "O que mudou".
- **Linha do tempo**: as versões são uma sequência, então têm uma linha vertical com um ponto
  por versão; a atual em amarelo (ipê), as anteriores em verde. A 1.0.0 leva o selo
  "Lançamento" (campo opcional `nome` em `novidades.ts`).
- **No computador, Minha unidade não mostra o botão** (ele já está no pé do menu lateral).
- **Datas**: `novidades.ts` guarda `AAAA-MM-DD` e a tela mostra "6 de outubro de 2026", lida ao
  meio-dia UTC para nenhum fuso trocar o dia.

## Fora (de propósito)

- Logo na barra/menu verde (decisão do Erick).
- Manifest/PWA e service worker (M2).
- O script do Playwright desta conferência ficou fora do repositório, como nas conferências
  anteriores (prints em `prints/logo-versao/`).

## Conferência no navegador (Chrome headless, contexto isolado)

320, 390 e 1366 px, claro e escuro, banco `portal_logo_versao`, API 8150, preview 5150:
- entrada com logo (1x no computador, 2x no celular; cartão branco no escuro), janela aberta pela
  entrada e logado, Minha unidade com o botão (celular: no fim da tela; computador: no menu);
- axe: 0 violações em entrada, janela e Minha unidade, nas 6 combinações;
- CSP: 0 violações, carregando o logo e os quatro ícones como imagem;
- sem rolagem lateral; Tab preso (região → Fechar → região…), Esc fecha e o foco volta ao botão
  "Versão 1.1.0".
- Único erro de console: o 401 de `/api/acesso/eu` na entrada (sem sessão), que já existia.
