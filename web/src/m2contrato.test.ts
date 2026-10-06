// Contrato do M2 no front (docs/superpowers/specs/m2-contrato.md, seções 4.2, 4.3 e 7): cada
// função de API chama a rota certa, com o método certo e o `X-Portal: 1` (as de recuperação são
// sem sessão, mas o cabeçalho vai igual), e os pontos de encaixe ainda não mudam nada.
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as notificacoes from './notificacoes/api'
import { destinoDepoisDoPrimeiroAcesso } from './notificacoes/ganchos'
import { rotasNotificacoes } from './notificacoes/rotas'
import * as recuperacao from './recuperacao/api'
import { rotasRecuperacao } from './recuperacao/rotas'

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

function chamada(fetch: ReturnType<typeof espiar>) {
  const [caminho, opcoes] = fetch.mock.calls[0] as unknown as [string, RequestInit]
  return {
    caminho,
    metodo: opcoes.method,
    corpo: opcoes.body ? JSON.parse(String(opcoes.body)) : undefined,
    cabecalhos: opcoes.headers,
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('notificacoes/api (épico A)', () => {
  it('estado é um GET', async () => {
    const fetch = espiar(200, { disponivel: false, chave_publica: null, este_aparelho: false })
    await notificacoes.lerEstadoDasNotificacoes()
    expect(chamada(fetch)).toMatchObject({ caminho: '/api/notificacoes', metodo: 'GET' })
  })

  it('inscrever é um PUT com o endpoint e as duas chaves', async () => {
    const fetch = espiar(204)
    const dados = { endpoint: 'https://fcm.googleapis.com/fcm/send/x', p256dh: 'p', auth: 'a' }
    await expect(notificacoes.inscreverEsteAparelho(dados)).resolves.toBeUndefined()
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/notificacoes/este-aparelho',
      metodo: 'PUT',
      corpo: dados,
      cabecalhos: { 'X-Portal': '1' },
    })
  })

  it('remover é um DELETE', async () => {
    const fetch = espiar(204)
    await notificacoes.removerEsteAparelho()
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/notificacoes/este-aparelho',
      metodo: 'DELETE',
    })
  })
})

describe('recuperacao/api (épico B)', () => {
  it('pedir manda só o login', async () => {
    const fetch = espiar(202, { mensagem: 'ok' })
    await recuperacao.pedirRecuperacao('1203')
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/acesso/recuperacao',
      metodo: 'POST',
      corpo: { login: '1203' },
      cabecalhos: { 'X-Portal': '1' },
    })
  })

  it('conferir e redefinir mandam o token no corpo, nunca na URL', async () => {
    let fetch = espiar(200, { unidade: { login: '1203', bloco: 1, apartamento: '203' } })
    await recuperacao.conferirLink('segredo')
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/acesso/recuperacao/conferir',
      corpo: { token: 'segredo' },
    })
    vi.unstubAllGlobals()
    fetch = espiar(200, {})
    const dados = { token: 'segredo', senha_nova: 'senha-boa', senha_nova_repetida: 'senha-boa' }
    await recuperacao.redefinirSenha(dados)
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/acesso/recuperacao/redefinir',
      metodo: 'POST',
      corpo: dados,
    })
  })
})

describe('pontos de encaixe (nada visível nesta onda)', () => {
  it('o primeiro acesso continua levando ao mural e não há rotas novas', () => {
    expect(destinoDepoisDoPrimeiroAcesso()).toBe('/avisos')
    expect(rotasNotificacoes).toEqual([])
    expect(rotasRecuperacao).toEqual([])
  })
})
