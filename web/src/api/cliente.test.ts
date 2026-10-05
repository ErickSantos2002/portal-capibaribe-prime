import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, comConsulta, ErroDaApi, MENSAGEM_SEM_CONEXAO, pedir } from './cliente'

function responder(status: number, corpo?: unknown) {
  const fetch = vi.fn(async () =>
    corpo === undefined
      ? new Response(null, { status })
      : new Response(JSON.stringify(corpo), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
  )
  vi.stubGlobal('fetch', fetch)
  return fetch
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('pedir', () => {
  it('manda X-Portal, cookies do próprio site e o corpo em JSON', async () => {
    const fetch = responder(200, { ok: true })
    await expect(pedir('POST', '/api/avisos', { titulo: 't' })).resolves.toEqual({ ok: true })
    const [caminho, opcoes] = fetch.mock.calls[0] as unknown as [string, RequestInit]
    expect(caminho).toBe('/api/avisos')
    expect(opcoes.method).toBe('POST')
    expect(opcoes.credentials).toBe('same-origin')
    expect(opcoes.headers).toMatchObject({
      'X-Portal': '1',
      'Content-Type': 'application/json',
    })
    expect(opcoes.body).toBe('{"titulo":"t"}')
  })

  it('leitura também leva X-Portal e não manda corpo', async () => {
    const fetch = responder(200, [])
    await api.get('/api/avisos')
    const opcoes = (fetch.mock.calls[0] as unknown as [string, RequestInit])[1]
    expect(opcoes.headers).toMatchObject({ 'X-Portal': '1' })
    expect(opcoes.body).toBeUndefined()
  })

  it('204 vira undefined', async () => {
    responder(204)
    await expect(api.post('/api/acesso/sair')).resolves.toBeUndefined()
  })

  it('erro da API vira ErroDaApi com código, mensagem, campos e extras', async () => {
    responder(423, {
      codigo: 'unidade_bloqueada',
      mensagem: 'Entrada bloqueada por 12 minutos.',
      minutos_restantes: 12,
    })
    const erro = await api.post('/api/acesso/entrar', {}).catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ErroDaApi)
    const e = erro as ErroDaApi
    expect([e.status, e.codigo, e.mensagem]).toEqual([
      423,
      'unidade_bloqueada',
      'Entrada bloqueada por 12 minutos.',
    ])
    expect(e.extras).toEqual({ minutos_restantes: 12 })
  })

  it('erro de validação aponta o campo', async () => {
    responder(422, {
      codigo: 'dados_invalidos',
      mensagem: 'Confira o celular.',
      campos: [{ campo: 'celular', mensagem: 'Confira o celular.' }],
    })
    const erro = (await api.post('/x', {}).catch((e: unknown) => e)) as ErroDaApi
    expect(erro.doCampo('celular')).toBe('Confira o celular.')
    expect(erro.doCampo('email')).toBeUndefined()
  })

  it('resposta sem o formato do Portal vira erro_inesperado', async () => {
    responder(500, { detail: 'Erro interno' })
    const erro = (await api.get('/x').catch((e: unknown) => e)) as ErroDaApi
    expect([erro.status, erro.codigo]).toEqual([500, 'erro_inesperado'])
  })

  it('sem internet vira sem_conexao, com mensagem para o morador', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    const erro = (await api.get('/x').catch((e: unknown) => e)) as ErroDaApi
    expect([erro.status, erro.codigo, erro.mensagem]).toEqual([0, 'sem_conexao', MENSAGEM_SEM_CONEXAO])
  })
})

describe('comConsulta', () => {
  it('monta a consulta, repete listas e ignora o que não veio', () => {
    expect(comConsulta('/api/avisos', { busca: 'fundação', arquivados: false, x: undefined })).toBe(
      '/api/avisos?busca=funda%C3%A7%C3%A3o&arquivados=false',
    )
    expect(comConsulta('/api/avisos/alcance', { blocos: [1, 3] })).toBe(
      '/api/avisos/alcance?blocos=1&blocos=3',
    )
    expect(comConsulta('/api/avisos/alcance', { blocos: [] })).toBe('/api/avisos/alcance')
  })
})
