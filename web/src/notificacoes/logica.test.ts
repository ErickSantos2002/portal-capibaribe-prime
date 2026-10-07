// Épico A do M2 · o que o aparelho sabe fazer, ativar e desativar, e os pontos de encaixe
// (spec m2-push.md, seção 3).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroDaApi } from '../api/cliente'
import { json } from '../acesso/apoioDeTeste'
import { aparelhoFalso, CHAVE, inscricaoFalsa, UA } from './apoioDeTeste'
import { comoLiberar, situacaoDoAparelho, plataforma } from './aparelho'
import { destinoDepoisDoPrimeiroAcesso, marcarOfertaVista } from './ganchos'
import { ativar, CHAVE_DONO, desativar, esquecerEsteAparelho, sincronizar } from './inscricao'

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

function api(respostas: Record<string, Response>) {
  const fetch = vi.fn(async (caminho: string, opcoes?: RequestInit) => {
    const resposta = respostas[`${opcoes?.method ?? 'GET'} ${caminho}`]
    return resposta ? resposta.clone() : json(404, { codigo: 'x', mensagem: 'não achou' })
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

const metodos = (fetch: ReturnType<typeof api>) =>
  fetch.mock.calls.map(([caminho, opcoes]) => `${opcoes?.method ?? 'GET'} ${caminho}`)

describe('situação do aparelho', () => {
  it('Android com Chrome: pronto para ativar', () => {
    aparelhoFalso({ ua: UA.android })
    expect(situacaoDoAparelho()).toBe('pronta')
    expect(plataforma()).toBe('android')
  })

  it('iPhone no Safari, sem instalar: precisa instalar primeiro', () => {
    aparelhoFalso({ ua: UA.iphone, push: false })
    expect(situacaoDoAparelho()).toBe('precisa_instalar')
    expect(plataforma()).toBe('iphone')
  })

  it('iPhone aberto pelo ícone (iOS 16.4+): pronto', () => {
    aparelhoFalso({ ua: UA.iphone, instalado: true })
    expect(situacaoDoAparelho()).toBe('pronta')
  })

  it('iPhone instalado sem push: iOS antigo', () => {
    aparelhoFalso({ ua: UA.iphone, instalado: true, push: false })
    expect(situacaoDoAparelho()).toBe('ios_antigo')
  })

  it('navegador sem push: sem suporte', () => {
    aparelhoFalso({ ua: UA.computador, push: false })
    expect(situacaoDoAparelho()).toBe('sem_suporte')
    expect(plataforma()).toBe('computador')
  })

  it('permissão negada: bloqueada', () => {
    aparelhoFalso({ permissao: 'denied' })
    expect(situacaoDoAparelho()).toBe('bloqueada')
  })

  it('como liberar depende do aparelho', () => {
    aparelhoFalso({ ua: UA.iphone, instalado: true, permissao: 'denied' })
    expect(comoLiberar()).toMatch(/Ajustes › Notificações › Capibaribe/)
    aparelhoFalso({ ua: UA.android, instalado: true, permissao: 'denied' })
    expect(comoLiberar()).toMatch(/segure o ícone Capibaribe/)
    aparelhoFalso({ ua: UA.android, permissao: 'denied' })
    expect(comoLiberar()).toMatch(/ícone à esquerda do endereço do site \(um cadeado ou dois tracinhos\)/)
  })
})

describe('ativar', () => {
  it('pede permissão primeiro (dentro do toque), inscreve com a chave e manda para a API', async () => {
    const { pedirPermissao, pushManager } = aparelhoFalso()
    const fetch = api({ 'PUT /api/notificacoes/este-aparelho': json(204) })
    const promessa = ativar(CHAVE, '1203')
    // O iPhone só mostra o pedido se ele sair na mesma volta do toque: nada antes dele.
    expect(pedirPermissao).toHaveBeenCalledTimes(1)
    expect(await promessa).toBe('ativa')
    const [opcoes] = pushManager.subscribe.mock.calls[0] as unknown as [PushSubscriptionOptionsInit]
    expect(opcoes.userVisibleOnly).toBe(true)
    expect((opcoes.applicationServerKey as Uint8Array).length).toBe(65)
    expect(metodos(fetch)).toEqual(['PUT /api/notificacoes/este-aparelho'])
    const corpo = JSON.parse(String(fetch.mock.calls[0][1]?.body))
    expect(corpo).toEqual({
      endpoint: 'https://fcm.googleapis.com/fcm/send/nova',
      p256dh: 'P'.repeat(87),
      auth: 'A'.repeat(22),
    })
  })

  it('pessoa negou: bloqueada, sem inscrever', async () => {
    const { pushManager } = aparelhoFalso({ resposta: 'denied' })
    const fetch = api({})
    expect(await ativar(CHAVE, '1203')).toBe('bloqueada')
    expect(pushManager.subscribe).not.toHaveBeenCalled()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('pessoa fechou o pedido: recusada, dá para tentar de novo', async () => {
    aparelhoFalso({ resposta: 'default' })
    api({})
    expect(await ativar(CHAVE, '1203')).toBe('recusada')
  })

  it('aproveita a inscrição que já existe com a mesma chave', async () => {
    const antiga = inscricaoFalsa()
    const { pushManager } = aparelhoFalso({ inscricao: antiga })
    const fetch = api({ 'PUT /api/notificacoes/este-aparelho': json(204) })
    await ativar(CHAVE, '1203')
    expect(pushManager.subscribe).not.toHaveBeenCalled()
    expect(JSON.parse(String(fetch.mock.calls[0][1]?.body)).endpoint).toBe(antiga.endpoint)
  })

  it('inscrição com outra chave (o servidor trocou o par): desfaz e inscreve de novo', async () => {
    const antiga = inscricaoFalsa(undefined, 'B' + 'Q'.repeat(85) + 'E')
    const { pushManager } = aparelhoFalso({ inscricao: antiga })
    api({ 'PUT /api/notificacoes/este-aparelho': json(204) })
    await ativar(CHAVE, '1203')
    expect(antiga.unsubscribe).toHaveBeenCalled()
    expect(pushManager.subscribe).toHaveBeenCalled()
  })

  it('a API recusou (10 aparelhos): desfaz a inscrição local e mostra a mensagem', async () => {
    const { nova } = aparelhoFalso()
    const mensagem = 'Este apartamento já tem 10 aparelhos com notificação. Desative em algum deles.'
    api({
      'PUT /api/notificacoes/este-aparelho': json(409, { codigo: 'limite_de_aparelhos', mensagem }),
    })
    const erro = await ativar(CHAVE, '1203').catch((e: unknown) => e)
    expect(erro).toBeInstanceOf(ErroDaApi)
    expect((erro as ErroDaApi).mensagem).toBe(mensagem)
    expect(nova.unsubscribe).toHaveBeenCalled()
  })
})

describe('dono da inscrição', () => {
  it('ativar guarda qual unidade ativou neste navegador', async () => {
    aparelhoFalso()
    api({ 'PUT /api/notificacoes/este-aparelho': json(204) })
    await ativar(CHAVE, '1203')
    expect(localStorage.getItem(CHAVE_DONO)).toBe('1203')
  })

  it('ao sair, o navegador esquece a inscrição', async () => {
    const atual = inscricaoFalsa()
    aparelhoFalso({ permissao: 'granted', inscricao: atual })
    localStorage.setItem(CHAVE_DONO, '1203')
    await esquecerEsteAparelho()
    expect(atual.unsubscribe).toHaveBeenCalled()
    expect(localStorage.getItem(CHAVE_DONO)).toBeNull()
  })
})

describe('desativar', () => {
  it('desfaz a inscrição do navegador e apaga na API', async () => {
    const atual = inscricaoFalsa()
    aparelhoFalso({ permissao: 'granted', inscricao: atual })
    const fetch = api({ 'DELETE /api/notificacoes/este-aparelho': json(204) })
    await desativar()
    expect(atual.unsubscribe).toHaveBeenCalled()
    expect(metodos(fetch)).toEqual(['DELETE /api/notificacoes/este-aparelho'])
  })

  it('sem inscrição no navegador, ainda apaga na API', async () => {
    aparelhoFalso({ permissao: 'granted' })
    const fetch = api({ 'DELETE /api/notificacoes/este-aparelho': json(204) })
    await desativar()
    expect(metodos(fetch)).toEqual(['DELETE /api/notificacoes/este-aparelho'])
  })
})

describe('sincronizar ao abrir o Portal', () => {
  beforeEach(() => localStorage.setItem(CHAVE_DONO, '1203'))
  const estado = (este_aparelho: boolean, chave_publica: string | null = CHAVE) =>
    json(200, { disponivel: chave_publica !== null, chave_publica, este_aparelho })

  it('sem permissão dada, não chama a API', async () => {
    aparelhoFalso({ permissao: 'default', inscricao: inscricaoFalsa() })
    const fetch = api({})
    expect(await sincronizar('1203')).toBe(false)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('sem inscrição no navegador, não chama a API', async () => {
    aparelhoFalso({ permissao: 'granted' })
    const fetch = api({})
    expect(await sincronizar('1203')).toBe(false)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('entrou de novo (sessão sem inscrição): guarda de novo, sem perguntar nada', async () => {
    const { pedirPermissao } = aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const fetch = api({
      'GET /api/notificacoes': estado(false),
      'PUT /api/notificacoes/este-aparelho': json(204),
    })
    expect(await sincronizar('1203')).toBe(true)
    expect(metodos(fetch)).toEqual(['GET /api/notificacoes', 'PUT /api/notificacoes/este-aparelho'])
    expect(pedirPermissao).not.toHaveBeenCalled()
  })

  it('já inscrito: só confere', async () => {
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const fetch = api({ 'GET /api/notificacoes': estado(true) })
    expect(await sincronizar('1203')).toBe(true)
    expect(metodos(fetch)).toEqual(['GET /api/notificacoes'])
  })

  it('servidor desligado: não faz nada', async () => {
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const fetch = api({ 'GET /api/notificacoes': estado(false, null) })
    expect(await sincronizar('1203')).toBe(false)
    expect(metodos(fetch)).toEqual(['GET /api/notificacoes'])
  })

  it('outra unidade ativou neste navegador: não herda a inscrição dela', async () => {
    // Revisão: a unidade A ativou e saiu; a B entra no mesmo navegador e não pode passar a
    // receber os avisos sem ter pedido.
    localStorage.setItem(CHAVE_DONO, '1101')
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const fetch = api({ 'GET /api/notificacoes': estado(false) })
    expect(await sincronizar('1203')).toBe(false)
    expect(metodos(fetch).filter((m) => m.startsWith('PUT'))).toEqual([])
  })

  it('sem saber quem ativou (localStorage vazio): não reinscreve', async () => {
    localStorage.clear()
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const fetch = api({ 'GET /api/notificacoes': estado(false) })
    expect(await sincronizar('1203')).toBe(false)
    expect(metodos(fetch).filter((m) => m.startsWith('PUT'))).toEqual([])
  })

  it('sem sessão (401) ou sem conexão: fica quieto', async () => {
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    api({ 'GET /api/notificacoes': json(401, { codigo: 'sem_sessao', mensagem: 'Entre.' }) })
    expect(await sincronizar('1203')).toBe(false)
  })
})

describe('oferta depois do primeiro acesso (uma vez por aparelho)', () => {
  it('na primeira vez leva a "Receber os avisos"; depois, ao mural', () => {
    expect(destinoDepoisDoPrimeiroAcesso()).toBe('/receber-avisos')
    marcarOfertaVista()
    expect(destinoDepoisDoPrimeiroAcesso()).toBe('/avisos')
  })

  it('sem localStorage (aba privada), oferece', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('bloqueado')
    })
    expect(destinoDepoisDoPrimeiroAcesso()).toBe('/receber-avisos')
  })
})
