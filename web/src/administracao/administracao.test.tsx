// Épico B · Administração: telas com a API de mentira (H-07, H-08, H-09, H-11).
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Eu, Papel, UnidadeRef } from '../api/tipos'
import { rotas } from '../rotas'
import { oQueFez, quemFez } from './frases'
import type { ItemHistorico, PainelAtivacao, UnidadeAdmin, UnidadePainel } from './tipos'

const ref = (login: string): UnidadeRef => ({
  login,
  bloco: Number(login[0]),
  apartamento: login.slice(1),
})

const ADMIN: Eu = {
  unidade: ref('1101'),
  papeis: ['admin'],
  gestao: true,
  admin: true,
  precisa_trocar_senha: false,
}

function json(status: number, corpo: unknown) {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

type Rota = (url: URL, init: RequestInit) => Response | Promise<Response>
let rotasFalsas: Record<string, Rota> = {}
let chamadas: { metodo: string; caminho: string; corpo?: unknown }[] = []

function api(extra: Record<string, Rota>, eu: Eu | null = ADMIN) {
  rotasFalsas = {
    'GET /api/acesso/eu': () =>
      eu ? json(200, eu) : json(401, { codigo: 'sem_sessao', mensagem: 'Entre de novo.' }),
    'GET /api/avisos/nao-lidos': () => json(200, { quantidade: 0 }),
    ...extra,
  }
  vi.stubGlobal(
    'fetch',
    vi.fn(async (caminho: string, init: RequestInit = {}) => {
      const url = new URL(caminho, 'https://portal.test')
      const metodo = init.method ?? 'GET'
      chamadas.push({
        metodo,
        caminho: url.pathname + url.search,
        corpo: init.body ? JSON.parse(String(init.body)) : undefined,
      })
      const rota = rotasFalsas[`${metodo} ${url.pathname}`]
      return rota ? rota(url, init) : json(404, { detail: 'Not Found' })
    }),
  )
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: [caminho] })
  render(<RouterProvider router={roteador} />)
  return roteador
}

function unidadePainel(login: string, extra: Partial<UnidadePainel> = {}): UnidadePainel {
  return {
    unidade: ref(login),
    andar: Number(login[1]),
    ativada: false,
    ativada_em: null,
    responsavel_nome: null,
    celular: null,
    papeis: [],
    ...extra,
  }
}

const PAINEL: PainelAtivacao = {
  resumo: { total: 4, ativadas: 2, percentual: 50 },
  blocos: [
    { numero: 1, nome: 'Bloco 1', total: 3, ativadas: 2, percentual: 67 },
    { numero: 2, nome: 'Bloco 2', total: 1, ativadas: 0, percentual: 0 },
  ],
  unidades: [
    unidadePainel('1001'),
    unidadePainel('1101', {
      ativada: true,
      ativada_em: '2026-10-29T23:14:00Z',
      responsavel_nome: 'Responsável fictício',
      celular: '81900000000',
      papeis: ['admin'],
    }),
    unidadePainel('1203', {
      ativada: true,
      ativada_em: '2026-11-02T12:00:00Z',
      responsavel_nome: 'Maria (fictícia)',
      celular: '81900000002',
    }),
    unidadePainel('2304'),
  ],
}

function ficha(login: string, extra: Partial<UnidadeAdmin> = {}): UnidadeAdmin {
  return {
    unidade: ref(login),
    andar: Number(login[1]),
    ativada: true,
    ativada_em: '2026-10-29T23:14:00Z',
    responsavel_nome: 'Maria (fictícia)',
    celular: '81912345678',
    email: null,
    papeis: [],
    bloqueada_ate: null,
    aparelhos_conectados: 2,
    ...extra,
  }
}

beforeEach(() => {
  localStorage.clear()
  chamadas = []
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('painel de ativação (H-07)', () => {
  it('mostra a adesão geral e por bloco, e a grade do 7º andar ao térreo', async () => {
    api({ 'GET /api/admin/unidades': () => json(200, PAINEL) })
    abrir('/unidades')

    expect(await screen.findByText('Bloco 1: 2 de 3 (67%)')).toBeTruthy()
    expect(screen.getByText('50%')).toBeTruthy()
    const bloco1 = screen.getByRole('region', { name: 'Bloco 1' })
    const apartamentos = within(bloco1)
      .getAllByRole('link')
      .map((a) => a.textContent)
    expect(apartamentos).toEqual(['203', '101', '001'])
    const admin = within(bloco1).getByRole('link', {
      name: 'Apartamento 101, já entrou, Administrador',
    })
    expect(admin.className).toBe('at ge')
    expect(admin.getAttribute('href')).toBe('/unidades/1101')
  })

  it('a lista mostra responsável, celular e data, e filtra pela API', async () => {
    api({
      'GET /api/admin/unidades': (url) =>
        url.searchParams.get('situacao') === 'nao_ativadas'
          ? json(200, { ...PAINEL, unidades: [PAINEL.unidades[0], PAINEL.unidades[3]] })
          : json(200, PAINEL),
    })
    abrir('/unidades')
    fireEvent.click(await screen.findByRole('button', { name: 'Lista com contatos' }))

    expect(await screen.findByText('Maria (fictícia)')).toBeTruthy()
    expect(screen.getByText('(81) 9 0000-0002')).toBeTruthy()
    expect(screen.getByText('entrou em 2 de novembro')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Ainda não' }))
    await waitFor(() => expect(screen.queryByText('Maria (fictícia)')).toBeNull())
    expect(screen.getAllByText('Ainda não entrou')).toHaveLength(2)
    expect(chamadas.map((c) => c.caminho)).toContain('/api/admin/unidades?situacao=nao_ativadas')
  })

  it('erro da API aparece com o botão de tentar de novo', async () => {
    api({
      'GET /api/admin/unidades': () =>
        json(403, { codigo: 'sem_permissao', mensagem: 'Esta função é só da administração.' }),
    })
    abrir('/unidades')
    expect(await screen.findByText('Esta função é só da administração.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Tentar de novo' })).toBeTruthy()
  })
})

describe('ficha da unidade e reset (H-08)', () => {
  it('mostra os dados da unidade', async () => {
    api({ 'GET /api/admin/unidades/1203': () => json(200, ficha('1203')) })
    abrir('/unidades/1203')

    expect(await screen.findByText('Maria (fictícia)')).toBeTruthy()
    expect(screen.getByRole('link', { name: '(81) 9 1234-5678' }).getAttribute('href')).toBe(
      'tel:+5581912345678',
    )
    expect(screen.getByText('Apartamento comum')).toBeTruthy()
    expect(screen.getByText('não informado')).toBeTruthy()
  })

  it('pede confirmação mostrando o que vai acontecer, e só reseta ao confirmar', async () => {
    api({
      'GET /api/admin/unidades/1203': () => json(200, ficha('1203')),
      'POST /api/admin/unidades/1203/resetar': () =>
        json(200, ficha('1203', { ativada: false, ativada_em: null, responsavel_nome: null,
          celular: null, aparelhos_conectados: 0 })),
    })
    abrir('/unidades/1203')
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar para a senha inicial' }))

    // U6: os títulos de seção da ficha são títulos de verdade.
    expect(screen.queryByRole('heading', { level: 2, name: 'Papel de gestão' })).toBeNull()
    const pergunta = screen.getByRole('heading', {
      name: 'Voltar o Bloco 1, 203 para a senha inicial?',
    })
    expect(document.activeElement).toBe(pergunta)
    expect(screen.getByText('A senha volta a ser a inicial (mudar123).')).toBeTruthy()
    expect(screen.getByText('Todos os aparelhos são desconectados.')).toBeTruthy()
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: 'Sim, voltar para a senha inicial' }))
    expect(await screen.findByText('Ainda não entrou')).toBeTruthy()
    expect(screen.getByText('Bloco 1, 203 voltou para a senha inicial.')).toBeTruthy()
    const reset = chamadas.find((c) => c.metodo === 'POST')
    expect(reset?.corpo).toEqual({ confirmo: true })
  })

  it('revisão U6: seções com título de verdade e sem "resetar" na tela', async () => {
    api({ 'GET /api/admin/unidades/1203': () => json(200, ficha('1203')) })
    abrir('/unidades/1203')
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Voltar para a senha inicial' }),
    ).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Papel de gestão' })).toBeTruthy()
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/reset/)
  })

  it('revisão U2: a confirmação rola para o meio da tela', async () => {
    const rolar = vi.fn()
    Element.prototype.scrollIntoView = rolar
    api({ 'GET /api/admin/unidades/1203': () => json(200, ficha('1203')) })
    abrir('/unidades/1203')
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar para a senha inicial' }))
    await waitFor(() => expect(rolar).toHaveBeenCalled())
    expect(rolar.mock.calls.at(-1)?.[0]).toMatchObject({ block: 'center' })
    expect((rolar.mock.contexts.at(-1) as Element).classList.contains('confirmacao')).toBe(true)
  })

  it('cancelar não reseta', async () => {
    api({ 'GET /api/admin/unidades/1203': () => json(200, ficha('1203')) })
    abrir('/unidades/1203')
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar para a senha inicial' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.getByRole('button', { name: 'Voltar para a senha inicial' })).toBeTruthy()
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)
  })

  it('o último admin: mostra a recusa da API', async () => {
    api({
      'GET /api/admin/unidades/1101': () => json(200, ficha('1101', { papeis: ['admin'] })),
      'POST /api/admin/unidades/1101/resetar': () =>
        json(409, {
          codigo: 'ultimo_admin',
          mensagem: 'Esta é a única unidade administradora. Dê o papel de administrador a outra unidade antes.',
        }),
    })
    abrir('/unidades/1101')
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar para a senha inicial' }))
    expect(
      screen.getByText('É o seu apartamento: você sai do Portal neste aparelho.'),
    ).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sim, voltar para a senha inicial' }))
    expect(
      (await screen.findByRole('alert')).textContent,
    ).toContain('Esta é a única unidade administradora.')
  })

  it('unidade que não existe', async () => {
    api({
      'GET /api/admin/unidades/9999': () =>
        json(404, { codigo: 'unidade_nao_encontrada', mensagem: 'Não achamos este apartamento.' }),
    })
    abrir('/unidades/9999')
    expect(await screen.findByText('Não achamos este apartamento.')).toBeTruthy()
  })
})

describe('papéis (H-09)', () => {
  function comPapeis(login: string, inicial: Papel[]) {
    let papeis = [...inicial]
    api({
      [`GET /api/admin/unidades/${login}`]: () => json(200, ficha(login, { papeis })),
      [`PUT /api/admin/unidades/${login}/papeis/comissao`]: () => {
        papeis = [...papeis, 'comissao'].sort() as Papel[]
        return json(200, ficha(login, { papeis }))
      },
      [`DELETE /api/admin/unidades/${login}/papeis/comissao`]: () => {
        papeis = papeis.filter((p) => p !== 'comissao')
        return json(200, ficha(login, { papeis }))
      },
      [`PUT /api/admin/unidades/${login}/papeis/admin`]: () => {
        papeis = [...papeis, 'admin'].sort() as Papel[]
        return json(200, ficha(login, { papeis }))
      },
    })
  }

  it('dar e tirar o papel de Comissão é direto, com recado', async () => {
    comPapeis('2304', [])
    abrir('/unidades/2304')
    fireEvent.click(await screen.findByRole('button', { name: 'Dar papel de Comissão' }))
    expect(await screen.findByText('Agora o Bloco 2, 304 é da Comissão.')).toBeTruthy()
    expect(screen.getByRole('img', { name: 'Bloco 2, apartamento 304' }).className).toContain(
      'gestao',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tirar papel de Comissão' }))
    expect(
      await screen.findByText('Papel de Comissão retirado. As opções somem na hora.'),
    ).toBeTruthy()
    expect(screen.getByText('Apartamento comum')).toBeTruthy()
  })

  it('dar o papel de administrador pede confirmação', async () => {
    comPapeis('2304', ['comissao'])
    abrir('/unidades/2304')
    fireEvent.click(await screen.findByRole('button', { name: 'Dar papel de administrador' }))
    expect(
      screen.getByRole('heading', { name: 'Dar papel de administrador ao Bloco 2, 304?' }),
    ).toBeTruthy()
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Sim, dar o papel' }))
    expect(await screen.findByText('Administrador e Comissão')).toBeTruthy()
  })

  it('unidade que não entrou não recebe papel', async () => {
    api({
      'GET /api/admin/unidades/4203': () =>
        json(200, ficha('4203', { ativada: false, ativada_em: null, responsavel_nome: null })),
    })
    abrir('/unidades/4203')
    expect(
      await screen.findByText('Só dá para dar papel a um apartamento que já entrou no Portal.'),
    ).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Dar papel de Comissão' })).toBeNull()
  })
})

function item(extra: Partial<ItemHistorico>): ItemHistorico {
  return {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: ref('1101'),
    acao: 'unidade_resetada',
    entidade: 'unidade',
    entidade_id: 7,
    unidade_afetada: ref('1106'),
    aviso_titulo: null,
    detalhes: {},
    ...extra,
  }
}

describe('histórico (H-11)', () => {
  it('escreve cada ação como frase, com quem fez', () => {
    expect(quemFez(item({}))).toBe('Bloco 1, 101')
    expect(oQueFez(item({}))).toBe('voltou o Bloco 1, 106 para a senha inicial')
    expect(
      oQueFez(item({ acao: 'papel_concedido', unidade_afetada: ref('2304'), detalhes: { papel: 'comissao' } })),
    ).toBe('deu papel de Comissão ao Bloco 2, 304')
    expect(
      oQueFez(item({ acao: 'papel_retirado', detalhes: { papel: 'admin', origem: 'reset' } })),
    ).toBe('tirou o papel de administrador do Bloco 1, 106, ao voltar para a senha inicial')
    const bloqueio = item({ acao: 'unidade_bloqueada', unidade: null, unidade_afetada: ref('5307') })
    expect(quemFez(bloqueio)).toBe('Portal')
    expect(oQueFez(bloqueio)).toBe(
      'bloqueou a entrada do Bloco 5, 307 por 15 minutos, depois de várias senhas erradas',
    )
    expect(
      oQueFez(item({ acao: 'aviso_publicado', entidade: 'aviso', unidade_afetada: null,
        aviso_titulo: 'Vistoria da obra' })),
    ).toBe('publicou o aviso “Vistoria da obra”')
    expect(oQueFez(item({ acao: 'primeiro_acesso' }))).toBe('entrou pela primeira vez')
    expect(oQueFez(item({ acao: 'papel_concedido', unidade_afetada: null }))).toBe(
      'deu papel de gestão a uma unidade',
    )
    expect(oQueFez(item({ acao: 'acao_nova' }))).toBe('acao nova')
  })

  it('lista do mais novo para o mais antigo e carrega mais', async () => {
    api({
      'GET /api/admin/historico': (url) =>
        url.searchParams.get('antes_de') === '2'
          ? json(200, { itens: [item({ id: 1, acao: 'primeiro_acesso' })], proximo: null })
          : json(200, {
              itens: [item({ id: 3 }), item({ id: 2, acao: 'senha_trocada' })],
              proximo: 2,
            }),
    })
    abrir('/historico')

    expect(await screen.findByText('Só o administrador vê. Ninguém consegue apagar.')).toBeTruthy()
    expect(await screen.findByText('voltou o Bloco 1, 106 para a senha inicial', { exact: false })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Carregar mais' }))
    expect(await screen.findByText('entrou pela primeira vez', { exact: false })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Carregar mais' })).toBeNull()
    const titulos = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(titulos).toEqual([
      'Bloco 1, 101 voltou o Bloco 1, 106 para a senha inicial',
      'Bloco 1, 101 trocou a senha',
      'Bloco 1, 101 entrou pela primeira vez',
    ])
  })
})
