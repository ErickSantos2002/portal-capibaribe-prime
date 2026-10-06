// Confirmação que abre na própria tela (apagar dados, arquivar, voltar para a senha inicial):
// rola o bloco inteiro para o meio da tela, longe das abas de baixo e do botão flutuante
// (revisão do M1, U2), e leva o foco ao título dele sem rolar de novo. Comum aos épicos.

function semMovimento(): boolean {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

export function centralizar(bloco: HTMLElement | null, foco?: HTMLElement | null): void {
  if (!bloco) return
  bloco.scrollIntoView?.({ block: 'center', behavior: semMovimento() ? 'auto' : 'smooth' })
  ;(foco ?? bloco).focus({ preventScroll: true })
}
