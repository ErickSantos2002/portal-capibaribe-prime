// Épico A do M2 · Notificações no aparelho (docs/superpowers/specs/m2-contrato.md, seção 4.2).
// Pertence ao épico A. Espelho de api/app/esquemas/push.py: o teste
// api/testes/test_contrato.py confere os campos.
import type { Categoria } from '../avisos/tipos'

/** `PUT /api/notificacoes/este-aparelho`: o `PushSubscription.toJSON()` achatado. */
export interface InscricaoPush {
  endpoint: string
  p256dh: string
  auth: string
}

/** `GET /api/notificacoes`. `disponivel` falso: o servidor está sem chaves (esconder a oferta). */
export interface EstadoNotificacoes {
  disponivel: boolean
  chave_publica: string | null
  este_aparelho: boolean
}

/** Corpo da notificação de aviso, lido pelo service worker (`public/sw.js`). */
export interface PushAviso {
  aviso_id: number
  titulo: string
  categoria: Categoria
  url: string
}
