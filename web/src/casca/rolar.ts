// Confirmação que abre na própria tela (apagar dados, arquivar, voltar para a senha inicial):
// rola o bloco inteiro para o meio da tela, longe das abas de baixo e do botão flutuante
// (revisão do M1, U2), e leva o foco ao título dele sem rolar de novo. Comum aos épicos.

function semMovimento(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

/** Onde termina o topo preso (`.topo`, sticky). Com o recado aberto ele cresce, e o
 *  scroll-padding do CSS (fixo) não sabe disso (revisão dos classificados, UX 8). */
function fimDoTopo(): number {
  const topo = document.querySelector<HTMLElement>('.topo')
  if (!topo) return 0
  const posicao = getComputedStyle(topo).position
  return posicao === 'sticky' || posicao === 'fixed' ? topo.getBoundingClientRect().bottom : 0
}

export function centralizar(bloco: HTMLElement | null, foco?: HTMLElement | null): void {
  if (!bloco) return
  const raiz = document.documentElement
  const s = getComputedStyle(raiz)
  const doCss = parseFloat(s.scrollPaddingTop) || 0
  // Um respiro abaixo do topo, como o do CSS.
  const topo = Math.max(doCss, fimDoTopo() ? fimDoTopo() + 8 : 0)
  // A altura que sobra entre o topo e as abas de baixo.
  const visivel = window.innerHeight - topo - (parseFloat(s.scrollPaddingBottom) || 0)
  // Revisões do M5 (U3): com letra grande, o bloco pode ser mais alto que a tela; no meio, o
  // começo dele (título e pergunta) ficava acima da vista. Então ele vai para o alto.
  const cabe = bloco.getBoundingClientRect().height <= visivel
  // O scroll-padding do topo passa a ser o do topo de agora só durante a rolagem.
  const antes = raiz.style.scrollPaddingTop
  if (topo > doCss) raiz.style.scrollPaddingTop = `${topo}px`
  bloco.scrollIntoView?.({ block: cabe ? 'center' : 'start', behavior: semMovimento() ? 'auto' : 'smooth' })
  raiz.style.scrollPaddingTop = antes
  ;(foco ?? bloco).focus({ preventScroll: true })
}
