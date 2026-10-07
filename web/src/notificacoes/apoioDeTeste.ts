// Apoio dos testes do épico A do M2: um aparelho de mentira (navegador, permissão, service
// worker e inscrição de push), trocado em `globalThis` como o jsdom não tem.
import { vi } from 'vitest'

export const UA = {
  android: 'Mozilla/5.0 (Linux; Android 14; SM-A145M) AppleWebKit/537.36 Chrome/130 Mobile Safari/537.36',
  iphone:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1',
  iphoneChrome:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 CriOS/130 Mobile/15E148 Safari/604.1',
  computador: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36',
}

// Chave pública VAPID de mentira: 65 bytes (0x04 + 64), em base64url sem `=`.
export const CHAVE = 'B' + 'A'.repeat(85) + 'E'

export interface InscricaoFalsa {
  endpoint: string
  options: { applicationServerKey: ArrayBuffer | null }
  unsubscribe: ReturnType<typeof vi.fn>
  toJSON: () => { endpoint: string; keys: { p256dh: string; auth: string } }
}

export function inscricaoFalsa(
  endpoint = 'https://fcm.googleapis.com/fcm/send/abc',
  chave: string | null = CHAVE,
): InscricaoFalsa {
  return {
    endpoint,
    options: { applicationServerKey: chave ? bytesDe(chave).buffer : null },
    unsubscribe: vi.fn(async () => true),
    toJSON: () => ({ endpoint, keys: { p256dh: 'P'.repeat(87), auth: 'A'.repeat(22) } }),
  }
}

function bytesDe(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/')
  const texto = atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4))
  return Uint8Array.from(texto, (c) => c.charCodeAt(0))
}

interface Opcoes {
  ua?: string
  instalado?: boolean
  push?: boolean
  permissao?: NotificationPermission
  /** O que o pedido de permissão responde. */
  resposta?: NotificationPermission
  inscricao?: InscricaoFalsa | null
}

/** Troca navegador, `Notification`, `PushManager` e `matchMedia`. Devolve os espiões. */
export function aparelhoFalso({
  ua = UA.android,
  instalado = false,
  push = true,
  permissao = 'default',
  resposta = 'granted',
  inscricao = null,
}: Opcoes = {}) {
  let atual = inscricao
  const nova = inscricaoFalsa('https://fcm.googleapis.com/fcm/send/nova')
  const pushManager = {
    getSubscription: vi.fn(async () => atual),
    subscribe: vi.fn(async () => {
      atual = nova
      return nova
    }),
  }
  const registro = {
    pushManager,
    showNotification: vi.fn(async () => undefined),
  }
  const serviceWorker = {
    register: vi.fn(async () => registro),
    getRegistration: vi.fn(async () => registro),
    ready: Promise.resolve(registro),
  }
  const pedirPermissao = vi.fn(async () => {
    estadoPermissao.valor = resposta
    return resposta
  })
  const estadoPermissao = { valor: permissao }
  vi.stubGlobal('navigator', {
    userAgent: ua,
    platform: ua.includes('iPhone') ? 'iPhone' : 'Linux',
    maxTouchPoints: ua.includes('Mobile') ? 5 : 0,
    language: 'pt-BR',
    ...(push ? { serviceWorker } : {}),
    ...(ua.includes('iPhone') ? { standalone: instalado } : {}),
  })
  if (push) {
    vi.stubGlobal('PushManager', function PushManager() {})
    vi.stubGlobal(
      'Notification',
      Object.assign(function Notification() {}, {
        get permission() {
          return estadoPermissao.valor
        },
        requestPermission: pedirPermissao,
      }),
    )
  } else {
    vi.stubGlobal('PushManager', undefined)
    vi.stubGlobal('Notification', undefined)
  }
  vi.stubGlobal(
    'matchMedia',
    vi.fn((consulta: string) => ({
      matches: consulta.includes('standalone') && instalado,
      addEventListener: () => {},
      removeEventListener: () => {},
    })),
  )
  return { pushManager, registro, serviceWorker, pedirPermissao, nova, estadoPermissao }
}
