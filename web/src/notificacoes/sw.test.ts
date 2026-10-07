// O service worker (web/public/sw.js), rodado num `self` falso: mostra a notificação com o
// título do aviso, o toque abre só caminhos /avisos/<n> do próprio Portal, e não há cache.
import { describe, expect, it, vi } from 'vitest'
// O arquivo como é servido (sem build): o `?raw` do Vite traz o texto.
import CODIGO from '../../public/sw.js?raw'

const ORIGEM = 'https://portal.exemplo'

interface Janela {
  url: string
  focus: ReturnType<typeof vi.fn>
  navigate: ReturnType<typeof vi.fn>
}

function janela(url: string, navegaFalha = false): Janela {
  const j: Janela = {
    url,
    focus: vi.fn(async () => j),
    navigate: vi.fn(async () => {
      if (navegaFalha) throw new TypeError('não controlada')
      return j
    }),
  }
  return j
}

function carregar(janelas: Janela[] = []) {
  const ouvintes: Record<string, (evento: unknown) => void> = {}
  const self = {
    location: { origin: ORIGEM },
    addEventListener: (tipo: string, f: (evento: unknown) => void) => (ouvintes[tipo] = f),
    skipWaiting: vi.fn(async () => undefined),
    registration: {
      showNotification: vi.fn(async () => undefined),
      pushManager: { subscribe: vi.fn() },
    },
    clients: {
      claim: vi.fn(async () => undefined),
      matchAll: vi.fn(async () => janelas),
      openWindow: vi.fn(async () => null),
    },
  }
  new Function('self', CODIGO)(self)

  async function disparar(tipo: string, evento: Record<string, unknown> = {}) {
    const esperas: Promise<unknown>[] = []
    ouvintes[tipo]?.({ ...evento, waitUntil: (p: Promise<unknown>) => esperas.push(p) })
    await Promise.all(esperas)
  }
  return { self, ouvintes, disparar }
}

const dadosDe = (corpo: unknown) => ({ data: { json: () => corpo } })
const notificacao = (url: unknown) => ({ notification: { close: vi.fn(), data: { url } } })

describe('sw.js · push', () => {
  it('mostra o título do aviso, com ícone, tag do aviso e o endereço para o toque', async () => {
    const { self, disparar } = carregar()
    await disparar(
      'push',
      dadosDe({ aviso_id: 7, titulo: 'Falta de água', categoria: 'geral', url: '/avisos/7' }),
    )
    expect(self.registration.showNotification).toHaveBeenCalledWith('Falta de água', {
      body: 'Aviso novo no Portal. Toque para ler.',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      lang: 'pt-BR',
      tag: 'aviso-7',
      data: { url: '/avisos/7' },
    })
  })

  it('aviso urgente diz que é urgente', async () => {
    const { self, disparar } = carregar()
    await disparar(
      'push',
      dadosDe({ aviso_id: 8, titulo: 'Elevador parado', categoria: 'urgente', url: '/avisos/8' }),
    )
    expect(self.registration.showNotification).toHaveBeenCalledWith(
      'Elevador parado',
      expect.objectContaining({ body: 'Aviso urgente no Portal. Toque para ler.' }),
    )
  })

  it('corpo estranho ainda mostra uma notificação que leva ao mural', async () => {
    const { self, disparar } = carregar()
    await disparar('push', {
      data: {
        json: () => {
          throw new SyntaxError('não é JSON')
        },
      },
    })
    expect(self.registration.showNotification).toHaveBeenCalledWith(
      'Aviso novo no Portal',
      expect.objectContaining({ tag: 'aviso', data: { url: '/avisos' } }),
    )
  })

  it('endereço de fora do Portal no corpo vira o mural', async () => {
    const { self, disparar } = carregar()
    await disparar(
      'push',
      dadosDe({ aviso_id: 9, titulo: 'X', categoria: 'geral', url: 'https://golpe.exemplo/a' }),
    )
    expect(self.registration.showNotification).toHaveBeenCalledWith(
      'X',
      expect.objectContaining({ data: { url: '/avisos' } }),
    )
  })
})

describe('sw.js · toque na notificação', () => {
  it('foca a janela do Portal já aberta e leva ao aviso', async () => {
    const aberta = janela(`${ORIGEM}/avisos`)
    const { self, disparar } = carregar([aberta])
    const evento = notificacao('/avisos/7')
    await disparar('notificationclick', evento)
    expect(evento.notification.close).toHaveBeenCalled()
    expect(aberta.focus).toHaveBeenCalled()
    expect(aberta.navigate).toHaveBeenCalledWith(`${ORIGEM}/avisos/7`)
    expect(self.clients.openWindow).not.toHaveBeenCalled()
  })

  it('sem janela aberta, abre uma nova no aviso', async () => {
    const { self, disparar } = carregar([])
    await disparar('notificationclick', notificacao('/avisos/7'))
    expect(self.clients.openWindow).toHaveBeenCalledWith(`${ORIGEM}/avisos/7`)
  })

  it('janela que não deixa navegar: abre uma nova', async () => {
    const { self, disparar } = carregar([janela(`${ORIGEM}/avisos`, true)])
    await disparar('notificationclick', notificacao('/avisos/7'))
    expect(self.clients.openWindow).toHaveBeenCalledWith(`${ORIGEM}/avisos/7`)
  })

  it.each([
    'https://golpe.exemplo/avisos/7',
    '//golpe.exemplo/avisos/7',
    '/minha-unidade',
    '/avisos/7/../../sair',
    'javascript:alert(1)',
    undefined,
  ])('só abre /avisos/<n> do próprio Portal (%s vira o mural)', async (url) => {
    const { self, disparar } = carregar([])
    await disparar('notificationclick', notificacao(url))
    expect(self.clients.openWindow).toHaveBeenCalledWith(`${ORIGEM}/avisos`)
  })
})

describe('sw.js · ciclo de vida e cache', () => {
  it('versão nova vale na hora (não há cache para ficar velho)', async () => {
    const { self, disparar } = carregar()
    await disparar('install')
    await disparar('activate')
    expect(self.skipWaiting).toHaveBeenCalled()
    expect(self.clients.claim).toHaveBeenCalled()
  })

  it('não intercepta requisições nem usa a Cache API', () => {
    const { ouvintes } = carregar()
    expect(ouvintes.fetch).toBeUndefined()
    expect(CODIGO).not.toMatch(/caches\./)
  })
})

describe('sw.js · inscrição trocada pelo navegador', () => {
  it('inscreve de novo com a mesma chave e avisa a API', async () => {
    const { self, disparar } = carregar()
    const nova = {
      toJSON: () => ({ endpoint: 'https://fcm.googleapis.com/fcm/send/novo', keys: { p256dh: 'P', auth: 'A' } }),
    }
    self.registration.pushManager.subscribe.mockResolvedValue(nova)
    const fetch = vi.fn(async () => new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    const chave = new Uint8Array([4, 1, 2])
    await disparar('pushsubscriptionchange', {
      oldSubscription: { options: { applicationServerKey: chave.buffer } },
    })
    expect(self.registration.pushManager.subscribe).toHaveBeenCalledWith({
      userVisibleOnly: true,
      applicationServerKey: chave.buffer,
    })
    expect(fetch).toHaveBeenCalledWith('/api/notificacoes/este-aparelho', {
      method: 'PUT',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Portal': '1' },
      body: JSON.stringify({
        endpoint: 'https://fcm.googleapis.com/fcm/send/novo',
        p256dh: 'P',
        auth: 'A',
      }),
    })
    vi.unstubAllGlobals()
  })

  it('sem a inscrição antiga, não faz nada (a tela reativa quando abrir)', async () => {
    const { self, disparar } = carregar()
    await disparar('pushsubscriptionchange', {})
    expect(self.registration.pushManager.subscribe).not.toHaveBeenCalled()
  })
})
