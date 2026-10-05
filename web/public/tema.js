// Aplica o tema escolhido antes do React desenhar, para a tela não piscar clara antes de ficar
// escura. Arquivo próprio (e não script embutido no HTML) porque a CSP proíbe script embutido.
// A mesma chave e os mesmos valores de web/src/casca/tema.ts.
try {
  if (localStorage.getItem('portal-tema') === 'escuro') {
    document.documentElement.dataset.tema = 'escuro'
  }
} catch {
  // Sem armazenamento (navegação privada restrita): fica o tema claro.
}
