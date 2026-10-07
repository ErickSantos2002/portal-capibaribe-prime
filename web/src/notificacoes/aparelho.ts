// O que este aparelho sabe fazer (H-05; spec m2-push.md, seção 3.3): receber push, se já está
// instalado na tela inicial, e o pedido de instalação que o navegador oferece.
//
// Tudo é lido na hora (nunca guardado no carregamento): a pessoa pode liberar a permissão nos
// ajustes e voltar para a mesma tela.

export type Plataforma = 'iphone' | 'android' | 'computador'

/** `pronta`: dá para pedir permissão e inscrever. O resto explica por que não. */
export type SituacaoDoAparelho = 'pronta' | 'precisa_instalar' | 'ios_antigo' | 'sem_suporte' | 'bloqueada'

export function plataforma(): Plataforma {
  const ua = navigator.userAgent
  // iPad com iPadOS 13+ diz ser um Mac; o toque denuncia.
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) {
    return 'iphone'
  }
  return /Android/.test(ua) ? 'android' : 'computador'
}

/** Safari de verdade no iPhone (Chrome, Firefox e Edge do iPhone têm o nome no agente). */
export function ehSafariDoIphone(): boolean {
  return plataforma() === 'iphone' && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(navigator.userAgent)
}

/** Aberto pelo ícone da tela inicial (ou como janela própria no computador). */
export function instalado(): boolean {
  const standalone = (navigator as Navigator & { standalone?: boolean }).standalone === true
  return standalone || (typeof matchMedia === 'function' && matchMedia('(display-mode: standalone)').matches)
}

export function suportaPush(): boolean {
  return (
    typeof navigator === 'object' &&
    'serviceWorker' in navigator &&
    typeof globalThis.PushManager === 'function' &&
    typeof globalThis.Notification === 'function'
  )
}

export function situacaoDoAparelho(): SituacaoDoAparelho {
  const iphone = plataforma() === 'iphone'
  // iPhone (iOS 16.4+): o push só existe com o Portal aberto pelo ícone (ADR-0006).
  if (iphone && !instalado()) return 'precisa_instalar'
  if (!suportaPush()) return iphone ? 'ios_antigo' : 'sem_suporte'
  if (Notification.permission === 'denied') return 'bloqueada'
  return 'pronta'
}

/** O caminho para liberar as notificações bloqueadas, no aparelho desta pessoa. */
export function comoLiberar(): string {
  if (plataforma() === 'iphone') {
    return 'No iPhone, abra Ajustes › Notificações › Capibaribe e ligue Permitir Notificações.'
  }
  if (plataforma() === 'android' && instalado()) {
    return 'No Android, toque e segure o ícone Capibaribe › Informações do app › Notificações › Permitir.'
  }
  return 'Toque no ícone à esquerda do endereço do site (um cadeado ou dois tracinhos) › Notificações › Permitir.'
}

// --- pedido de instalação (Chrome, Edge, Samsung Internet) -------------------------------------

/** O `beforeinstallprompt`, que o TypeScript ainda não conhece. */
interface PedidoDeInstalacao extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

let pedido: PedidoDeInstalacao | null = null
const ouvintes = new Set<() => void>()
const avisar = () => ouvintes.forEach((ouvinte) => ouvinte())

/** Chamado uma vez ao abrir o Portal: o navegador oferece instalar só no começo da página. */
export function ouvirPedidoDeInstalacao(): void {
  addEventListener('beforeinstallprompt', (evento) => {
    // Guarda para o botão "Instalar na tela inicial", em vez da faixa do navegador.
    evento.preventDefault()
    pedido = evento as PedidoDeInstalacao
    avisar()
  })
  addEventListener('appinstalled', () => {
    pedido = null
    avisar()
  })
}

export function podeInstalar(): boolean {
  return pedido !== null
}

/** Para o `useSyncExternalStore` da tela. */
export function acompanharInstalacao(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte)
  return () => ouvintes.delete(ouvinte)
}

/** Abre a janela de instalação do navegador. O pedido só vale uma vez. */
export async function pedirInstalacao(): Promise<'aceitou' | 'recusou' | 'indisponivel'> {
  const atual = pedido
  if (!atual) return 'indisponivel'
  pedido = null
  avisar()
  await atual.prompt()
  const { outcome } = await atual.userChoice
  return outcome === 'accepted' ? 'aceitou' : 'recusou'
}
