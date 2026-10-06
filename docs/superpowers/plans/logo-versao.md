# Plano · logo, ícone e versão com janela de novidades

Branch `web/logo-versao`. Decisões e dúvidas em `docs/superpowers/duvidas-logo-versao.md`.

## Objetivo

O Portal ganha a cara do Capibaribe Prime Residence (logo na entrada, ícone na aba e na tela
inicial) e passa a dizer em que versão está e o que mudou, na voz do morador.

## Tarefas (TDD: teste falhando antes do código)

1. **Imagens** — `scripts/dev/gerar-icones.py` (Pillow + numpy) gera, a partir do logo com fundo
   branco (fora do repo): `web/src/marca/logo{,@2x}.webp` (alvo < 80 KB) e, só com a espiral,
   `web/public/favicon.ico` (16/32/48, transparente), `apple-touch-icon.png` 180,
   `icon-192.png`, `icon-512.png` (fundo `--papel`). Sai o `favicon.svg` antigo.
2. **Ícones no `index.html`** — teste de build (`testes/cabecalhos.test.ts`): os links existem, os
   arquivos respondem 200 com o tipo certo, nada de terceiros (CSP `default-src 'self'`).
3. **Versão** — `version` do `web/package.json` → `1.1.0`, injetada pelo Vite como
   `__VERSAO__` (`define`). Teste: `__VERSAO__` é a do package.json.
4. **Novidades** — `web/src/sobre/novidades.ts` tipado. Teste: a primeira é a versão atual;
   semver; ordem decrescente; nenhuma data no futuro; itens não vazios.
5. **Logo** — componente `Logo` (1x/2x, `alt="Capibaribe Prime Residence"`, largura e altura
   reservadas). No escuro, cartão claro. Entrada: substitui a placa "Capibaribe / PRIME"; o h1
   continua. Teste de tela.
6. **Janela de versão** — `BotaoVersao` (botão "Versão 1.1.0") abre um `<dialog>` modal nativo
   (o app não tem componente de janela): logo, título ligado por `aria-labelledby`, "O que mudou"
   por versão, botão "Fechar"; Esc fecha; o foco volta ao botão. Lugares: rodapé do menu
   lateral (computador), fim de Minha unidade (celular), rodapé da entrada. Testes de tela.
7. **README** — seção "Versões" com a regra.
8. **Conferência** — lint, typecheck, test, build; Playwright próprio (320/390/1366, claro e
   escuro, axe, CSP, rolagem lateral, teclado) com prints em
   `docs/superpowers/prints/logo-versao/`.

## Fora

Manifest/PWA (M2), service worker, logo na barra verde.
