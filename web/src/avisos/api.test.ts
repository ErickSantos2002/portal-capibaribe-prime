// Contrato do épico C (spec do M1, seção 4.4): abrir o aviso só lê; a leitura é um POST à parte
// (GET não altera nada: navegação vinda de outro site não pode gravar leitura).
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as avisos from './api'

function espiar(status = 200, corpo: unknown = {}) {
  const fetch = vi.fn(async () =>
    status === 204
      ? new Response(null, { status })
      : new Response(JSON.stringify(corpo), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
  )
  vi.stubGlobal('fetch', fetch)
  return fetch
}

afterEach(() => vi.unstubAllGlobals())

describe('avisos/api', () => {
  it('abrir o aviso é um GET', async () => {
    const fetch = espiar()
    await avisos.abrirAviso(12)
    const [caminho, opcoes] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect([caminho, opcoes.method]).toEqual(['/api/avisos/12', 'GET'])
  })

  it('marcar como lido é um POST que responde 204', async () => {
    const fetch = espiar(204)
    await expect(avisos.marcarLido(12)).resolves.toBeUndefined()
    const [caminho, opcoes] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect([caminho, opcoes.method]).toEqual(['/api/avisos/12/lido', 'POST'])
    expect(opcoes.headers).toMatchObject({ 'X-Portal': '1' })
  })
})
