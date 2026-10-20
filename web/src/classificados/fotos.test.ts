// Classificados · enviar uma foto (ADR-0012): o caminho do M3 com as rotas dos classificados.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ErroDaApi } from '../api/cliente'
import type { Ferramentas } from '../arquivos/comprimir'
import { enviarFoto, LIMITE_FOTO, MSG_FOTO_NAO_CHEGOU, MSG_TIPO_FOTO, problemaDaFoto } from './fotos'

const URL_DO_ENVIO = 'https://conta.r2.cloudflarestorage.com/portal/envios/abc?assinado=1'

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } })
}

function rede(put: () => Promise<Response> = async () => new Response(null, { status: 200 })) {
  const fetch = vi.fn(async (caminho: string, opcoes: RequestInit = {}) => {
    if (caminho === '/api/classificados/fotos') {
      return json(201, { foto_id: 41, url: URL_DO_ENVIO, content_type: 'image/webp', expira_em: 'x' })
    }
    if (caminho === '/api/classificados/fotos/41/confirmar') return json(200, { id: 41 })
    if (caminho === URL_DO_ENVIO && opcoes.method === 'PUT') return put()
    return json(404, { codigo: 'nao_encontrado', mensagem: 'Não achamos.' })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** O navegador de mentira: a foto de 4000 × 3000 vira um WEBP pequeno (o GPS sai junto). */
function ferramentas(saida: Blob | null = new Blob([new Uint8Array(500)], { type: 'image/webp' })): Ferramentas {
  return { medir: vi.fn(async () => ({ largura: 4000, altura: 3000 })), regravar: vi.fn(async () => saida) }
}

afterEach(() => vi.unstubAllGlobals())

describe('enviarFoto', () => {
  it('comprime, pede às rotas dos classificados, faz o PUT sem cookie e confirma', async () => {
    const fetch = rede()
    const foto = new File([new Uint8Array(5000)], 'sofa.jpg', { type: 'image/jpeg' })
    await expect(enviarFoto(foto, ferramentas())).resolves.toBe(41)
    const [pedido, put, confirmacao] = fetch.mock.calls.map(([c, o]) => ({ c, o: (o ?? {}) as RequestInit }))
    expect(pedido.c).toBe('/api/classificados/fotos')
    // O tamanho declarado é o da foto comprimida (regravada: o JPEG perde o GPS).
    expect(JSON.parse(String(pedido.o.body))).toEqual({ tipo: 'image/webp', tamanho_bytes: 500 })
    expect(put.c).toBe(URL_DO_ENVIO)
    expect(put.o.credentials).toBe('omit')
    expect(put.o.headers).toEqual({ 'Content-Type': 'image/webp' })
    expect(confirmacao.c).toBe('/api/classificados/fotos/41/confirmar')
  })

  it('PDF nem é pedido', async () => {
    const fetch = rede()
    const pdf = new File(['%PDF'], 'conta.pdf', { type: 'application/pdf' })
    const erro = (await enviarFoto(pdf, ferramentas()).catch((e: unknown) => e)) as ErroDaApi
    expect(erro.mensagem).toBe(MSG_TIPO_FOTO)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('o PUT que falha vira "A foto não chegou ao Portal"', async () => {
    rede(async () => new Response(null, { status: 403 }))
    const foto = new File([new Uint8Array(10)], 'a.png', { type: 'image/png' })
    const erro = (await enviarFoto(foto, ferramentas(null)).catch((e: unknown) => e)) as ErroDaApi
    expect(erro.codigo).toBe('arquivo_nao_chegou')
    expect(erro.mensagem).toBe(MSG_FOTO_NAO_CHEGOU)
  })

  it('o limite e as mensagens são os da API', () => {
    expect(LIMITE_FOTO).toBe(10 * 1024 * 1024)
    expect(problemaDaFoto({ type: 'image/gif', size: 10 })).toBe(MSG_TIPO_FOTO)
    expect(problemaDaFoto({ type: 'image/jpeg', size: LIMITE_FOTO + 1 })).toBe('A foto pode ter até 10 MB.')
    expect(problemaDaFoto({ type: 'image/jpeg', size: LIMITE_FOTO })).toBeNull()
  })
})
