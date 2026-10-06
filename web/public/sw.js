// Service worker do Portal Capibaribe Prime (M2, H-05 e H-13). Escrito à mão, sem build.
//
// Faz só três coisas: mostra a notificação de aviso novo, abre o aviso quando a pessoa toca
// nela, e refaz a inscrição se o navegador trocá-la sozinho.
//
// **Sem cache, de propósito.** Não há ouvinte de `fetch` nem Cache API: toda tela vem da rede,
// como sem o service worker. O Portal muda de versão com frequência e um cache de páginas
// prenderia o morador numa versão velha (spec do M2, seção 4.2). Por isso também `skipWaiting`
// e `clients.claim`: a versão nova deste arquivo vale na hora, sem nada para ficar incoerente.

const MURAL = '/avisos'
const CAMINHO_DE_AVISO = /^\/avisos\/[0-9]+$/

/** Só caminhos `/avisos/<n>` do próprio Portal; qualquer outra coisa vira o mural. */
function caminhoSeguro(url) {
  return typeof url === 'string' && CAMINHO_DE_AVISO.test(url) ? url : MURAL
}

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (evento) => {
  evento.waitUntil(self.clients.claim())
})

self.addEventListener('push', (evento) => {
  let dados = {}
  try {
    dados = (evento.data && evento.data.json()) || {}
  } catch {
    dados = {}
  }
  const titulo =
    typeof dados.titulo === 'string' && dados.titulo.trim() ? dados.titulo : 'Aviso novo no Portal'
  const id = Number.isInteger(dados.aviso_id) ? dados.aviso_id : null
  const urgente = dados.categoria === 'urgente'
  evento.waitUntil(
    self.registration.showNotification(titulo, {
      body: urgente
        ? 'Aviso urgente no Portal. Toque para ler.'
        : 'Aviso novo no Portal. Toque para ler.',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      lang: 'pt-BR',
      // Mesmo aviso duas vezes (o serviço de push repetiu) vira uma notificação só.
      tag: id === null ? 'aviso' : `aviso-${id}`,
      data: { url: caminhoSeguro(dados.url) },
    }),
  )
})

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close()
  const destino = new URL(
    caminhoSeguro(evento.notification.data && evento.notification.data.url),
    self.location.origin,
  ).href
  evento.waitUntil(abrir(destino))
})

async function abrir(destino) {
  const janelas = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
  const aberta = janelas.find((j) => new URL(j.url).origin === self.location.origin)
  if (aberta) {
    try {
      await aberta.focus()
      await aberta.navigate(destino)
      return
    } catch {
      // Janela que o service worker não controla não navega: abre outra.
    }
  }
  await self.clients.openWindow(destino)
}

// O navegador trocou a inscrição (expirou ou renovou): inscreve de novo com a mesma chave e
// manda para a API, com o cookie da sessão deste aparelho. Sem a antiga, a tela de Minha
// unidade refaz quando o Portal abrir.
self.addEventListener('pushsubscriptionchange', (evento) => {
  const chave = evento.oldSubscription && evento.oldSubscription.options.applicationServerKey
  if (!chave) return
  evento.waitUntil(reinscrever(chave))
})

async function reinscrever(chave) {
  const nova = await self.registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: chave,
  })
  const { endpoint, keys } = nova.toJSON()
  await fetch('/api/notificacoes/este-aparelho', {
    method: 'PUT',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-Portal': '1' },
    body: JSON.stringify({ endpoint, p256dh: keys.p256dh, auth: keys.auth }),
  })
}
