// Épico A do M2 · pontos de encaixe nas telas comuns e do M1 (spec do M2, seção 7; spec
// m2-push.md, seção 3). As telas que chamam estas funções não mudam.
import { ouvirPedidoDeInstalacao } from './aparelho'
import { sincronizar } from './inscricao'

/** Guardado em `localStorage` quando a tela "Receber os avisos" já apareceu neste aparelho. */
export const CHAVE_OFERTA = 'portal-oferta-avisos'

/**
 * Chamado uma vez em `main.tsx`, depois de montar o app: registra `/sw.js`, guarda o pedido
 * de instalação do navegador e mantém a inscrição de quem já ativou.
 *
 * `updateViaCache: 'none'`: o navegador busca o `sw.js` novo sem passar pelo cache HTTP. O
 * service worker não guarda páginas (ver `public/sw.js`).
 */
export function registrarServiceWorker(): void {
  if (typeof navigator !== 'object' || !('serviceWorker' in navigator)) return
  ouvirPedidoDeInstalacao()
  navigator.serviceWorker
    .register('/sw.js', { scope: '/', updateViaCache: 'none' })
    .then(() => sincronizar())
    .catch(() => {
      // Sem service worker o Portal funciona igual; só não há notificação neste aparelho.
    })
}

/** Para onde o primeiro acesso leva (H-05): a oferta "Instalar" e "Ativar notificações" na
 *  primeira vez deste aparelho; depois, o mural. */
export function destinoDepoisDoPrimeiroAcesso(): string {
  try {
    if (localStorage.getItem(CHAVE_OFERTA)) return '/avisos'
  } catch {
    // Sem localStorage (aba privada): oferece. O primeiro acesso só acontece uma vez.
  }
  return '/receber-avisos'
}

export function marcarOfertaVista(): void {
  try {
    localStorage.setItem(CHAVE_OFERTA, '1')
  } catch {
    // Sem localStorage, a oferta pode aparecer de novo; não atrapalha nada.
  }
}
