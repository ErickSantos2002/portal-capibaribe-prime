// Ativar, desativar e sincronizar a inscrição de push deste aparelho (H-05; spec m2-push.md,
// seção 3.3). A inscrição mora em dois lugares: no navegador (`PushSubscription`) e na API (a
// sessão deste aparelho). As funções daqui mantêm os dois juntos.
import { inscreverEsteAparelho, lerEstadoDasNotificacoes, removerEsteAparelho } from './api'
import type { EstadoNotificacoes, InscricaoPush } from './tipos'

const ESPERA_DO_SERVICE_WORKER_MS = 10_000

export type ResultadoDeAtivar = 'ativa' | 'recusada' | 'bloqueada'

/** Chave pública VAPID (base64url) → bytes, o formato do `applicationServerKey`. */
export function bytesDaChave(chave: string): Uint8Array<ArrayBuffer> {
  const base64 = chave.replace(/-/g, '+').replace(/_/g, '/')
  const texto = atob(base64 + '='.repeat((4 - (base64.length % 4)) % 4))
  return Uint8Array.from(texto, (c) => c.charCodeAt(0))
}

function mesmaChave(inscricao: PushSubscription, chave: string): boolean {
  const atual = inscricao.options.applicationServerKey
  if (!atual) return false
  const a = new Uint8Array(atual)
  const b = bytesDaChave(chave)
  return a.length === b.length && a.every((byte, i) => byte === b[i])
}

function achatar(inscricao: PushSubscription): InscricaoPush {
  const { endpoint, keys } = inscricao.toJSON()
  return { endpoint: endpoint ?? inscricao.endpoint, p256dh: keys?.p256dh ?? '', auth: keys?.auth ?? '' }
}

async function registro(): Promise<ServiceWorkerRegistration> {
  const existente = await navigator.serviceWorker.getRegistration('/')
  if (!existente) await navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' })
  let tempo: ReturnType<typeof setTimeout> | undefined
  const espera = new Promise<never>((_, rejeitar) => {
    tempo = setTimeout(
      () => rejeitar(new Error('o service worker não ficou pronto')),
      ESPERA_DO_SERVICE_WORKER_MS,
    )
  })
  try {
    return await Promise.race([navigator.serviceWorker.ready, espera])
  } finally {
    clearTimeout(tempo)
  }
}

/** A inscrição deste navegador, se houver. */
export async function inscricaoLocal(): Promise<PushSubscription | null> {
  const existente = await navigator.serviceWorker.getRegistration('/')
  return existente ? existente.pushManager.getSubscription() : null
}

async function inscreverNoNavegador(chave: string): Promise<PushSubscription> {
  const { pushManager } = await registro()
  const atual = await pushManager.getSubscription()
  if (atual && mesmaChave(atual, chave)) return atual
  // Chave diferente: o servidor trocou o par VAPID. A inscrição velha não serve mais.
  if (atual) await atual.unsubscribe()
  return pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: bytesDaChave(chave) })
}

/**
 * Chamar **direto do toque** no botão: o pedido de permissão é a primeira coisa (o iPhone só
 * mostra o pedido se ele sair do toque). Erro da API desfaz a inscrição do navegador e sobe
 * (`ErroDaApi`), para não ficar meio ligada.
 */
export async function ativar(chave: string): Promise<ResultadoDeAtivar> {
  const permissao = await Notification.requestPermission()
  if (permissao === 'denied') return 'bloqueada'
  if (permissao !== 'granted') return 'recusada'
  const inscricao = await inscreverNoNavegador(chave)
  try {
    await inscreverEsteAparelho(achatar(inscricao))
  } catch (erro) {
    await inscricao.unsubscribe().catch(() => false)
    throw erro
  }
  return 'ativa'
}

/** Logo depois de ativar: uma notificação local, para a pessoa ver como os avisos vão chegar.
 *  Não passa pelo servidor (não prova a entrega; isso só o aviso de verdade prova). */
export async function mostrarExemplo(): Promise<void> {
  try {
    const existente = await navigator.serviceWorker.getRegistration('/')
    await existente?.showNotification('Notificações ligadas', {
      body: 'É assim que os avisos do condomínio vão chegar.',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      lang: 'pt-BR',
      tag: 'exemplo',
      data: { url: '/avisos' },
    })
  } catch {
    // Só um exemplo: se não aparecer, nada muda.
  }
}

/** Desfaz no navegador primeiro: mesmo sem conexão, este aparelho para de receber (o serviço
 *  de push passa a responder 410 e a API apaga a inscrição no próximo aviso). */
export async function desativar(): Promise<void> {
  const atual = await inscricaoLocal().catch(() => null)
  await atual?.unsubscribe().catch(() => false)
  await removerEsteAparelho()
}

/**
 * Ao abrir o Portal: quem já ativou continua recebendo depois de entrar de novo ou trocar a
 * senha (a inscrição na API some com a sessão; a do navegador continua). Só faz requisição se
 * a permissão já foi dada e o navegador tem inscrição. Nunca levanta. Devolve se este aparelho
 * está recebendo.
 */
export async function sincronizar(estado?: EstadoNotificacoes): Promise<boolean> {
  try {
    if (typeof Notification !== 'function' || Notification.permission !== 'granted') return false
    if (!('serviceWorker' in navigator)) return false
    const local = await inscricaoLocal()
    if (!local) return false
    const atual = estado ?? (await lerEstadoDasNotificacoes())
    if (!atual.disponivel || !atual.chave_publica) return false
    if (atual.este_aparelho && mesmaChave(local, atual.chave_publica)) return true
    const inscricao = await inscreverNoNavegador(atual.chave_publica)
    await inscreverEsteAparelho(achatar(inscricao))
    return true
  } catch {
    return false
  }
}
