// Confirmação que abre na própria tela (apagar dados, arquivar, voltar para a senha inicial):
// rola o bloco inteiro para o meio da tela, longe das abas de baixo e do botão flutuante
// (revisão do M1, U2), e leva o foco ao título dele sem rolar de novo. Comum aos épicos.

function semMovimento(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

/** A altura que sobra entre o topo fixo e as abas de baixo (o scroll-padding do html). */
function alturaVisivel(): number {
  const s = getComputedStyle(document.documentElement)
  return window.innerHeight - (parseFloat(s.scrollPaddingTop) || 0) - (parseFloat(s.scrollPaddingBottom) || 0)
}

export function centralizar(bloco: HTMLElement | null, foco?: HTMLElement | null): void {
  if (!bloco) return
  // Revisões do M5 (U3): com letra grande, o bloco pode ser mais alto que a tela; no meio, o
  // começo dele (título e pergunta) ficava acima da vista. Então ele vai para o alto.
  const cabe = bloco.getBoundingClientRect().height <= alturaVisivel()
  bloco.scrollIntoView?.({ block: cabe ? 'center' : 'start', behavior: semMovimento() ? 'auto' : 'smooth' })
  ;(foco ?? bloco).focus({ preventScroll: true })
}
