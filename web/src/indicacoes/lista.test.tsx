// Indicações · a lista (spec, seção 3.1) e o lugar novo no menu (seção 3.4), com a API de
// mentira e o Portal inteiro montado.
import { act, cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { apiIndicacoes, resumo } from './apoioDeTeste'

beforeAll(() => {
  const proto = HTMLDialogElement.prototype
  proto.showModal ??= function (this: HTMLDialogElement) {
    this.open = true
  }
  proto.close ??= function (this: HTMLDialogElement) {
    if (!this.open) return
    this.open = false
    this.dispatchEvent(new Event('close'))
  }
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const ADMIN = eu(['admin'], false, '1101')

const ITENS = [
  resumo(3, {
    nome: 'Marcenaria Silva',
    recomendam: 4,
    nao_recomendam: 1,
    trecho: {
      unidade: { login: '2304', bloco: 2, apartamento: '304' },
      recomenda: true,
      comentario: 'Caprichoso e pontual.',
      em: '2026-10-15T15:00:00Z',
    },
  }),
  resumo(5, { nome: 'Fios & Cia', categoria: { id: 5, nome: 'Eletricista' }, recomendam: 1 }),
]

describe('lista de indicações', () => {
  it('mostra os cartões na ordem da API, com recomendam, não recomendam e a placa', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }) })
    abrir('/indicacoes')
    const cartoes = await screen.findAllByRole(
      'link',
      { name: /Marcenaria Silva|Fios & Cia/ },
      { timeout: 4000 },
    )
    expect(cartoes.map((c) => c.getAttribute('href'))).toEqual(['/indicacoes/3', '/indicacoes/5'])
    const primeiro = cartoes[0]
    expect(primeiro.textContent).toContain('Móveis planejados')
    expect(primeiro.textContent).toContain('4 vizinhos recomendam')
    expect(primeiro.textContent).toContain('1 não recomenda')
    expect(primeiro.textContent).toContain('Caprichoso e pontual.')
    expect(within(primeiro).getByRole('img', { name: 'Bloco 2, apartamento 304' })).toBeTruthy()
    expect(cartoes[1].textContent).toContain('1 vizinho recomenda')
    expect(cartoes[1].textContent).not.toContain('não recomenda')
    expect(screen.getByRole('heading', { level: 1, name: 'Indicações' })).toBeTruthy()
  })

  it('tocar numa categoria filtra e marca aria-pressed; "Todos" volta', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }),
      'GET /api/indicacoes?categoria=5': json(200, { itens: [ITENS[1]], com_aviso: null }),
    })
    abrir('/indicacoes')
    const faixa = await screen.findByRole('navigation', { name: 'Categorias' })
    const todos = within(faixa).getByRole('button', { name: 'Todos' })
    expect(todos.getAttribute('aria-pressed')).toBe('true')
    const botoes = within(faixa).getAllByRole('button')
    expect(botoes[0]).toBe(todos)
    fireEvent.click(within(faixa).getByRole('button', { name: 'Eletricista' }))
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/indicacoes?categoria=5')).toBe(true),
    )
    expect(within(faixa).getByRole('button', { name: 'Eletricista' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
    expect(todos.getAttribute('aria-pressed')).toBe('false')
    await waitFor(() => expect(screen.queryByText('Marcenaria Silva')).toBeNull())
    fireEvent.click(todos)
    expect(await screen.findByText('Marcenaria Silva')).toBeTruthy()
  })

  it('a busca chama a API com ?busca= depois de digitar', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }),
      'GET /api/indicacoes?busca=joao': json(200, { itens: [], com_aviso: null }),
    })
    abrir('/indicacoes')
    const campo = await screen.findByLabelText(/Procurar: nome ou serviço/)
    fireEvent.change(campo, { target: { value: ' joao ' } })
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/indicacoes?busca=joao')).toBe(true),
    )
    // A frase aparece na lista e no anúncio do leitor de tela.
    await waitFor(() =>
      expect(document.querySelector('p.vazio')?.textContent).toBe('Nenhuma indicação encontrada.'),
    )
  })

  it('lista vazia mostra o convite e o botão Indicar alguém', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: [], com_aviso: null }) })
    abrir('/indicacoes')
    expect(
      await screen.findByText('Ainda não tem indicação aqui. Seja o primeiro a indicar alguém.'),
    ).toBeTruthy()
    const indicar = screen.getAllByRole('link', { name: /Indicar alguém/ })
    expect(indicar.length).toBeGreaterThan(0)
    expect(indicar.every((l) => l.getAttribute('href') === '/indicacoes/nova')).toBe(true)
  })

  it('o botão flutuante "Indicar alguém" leva ao formulário', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }) })
    abrir('/indicacoes')
    await screen.findByText('Marcenaria Silva')
    const botao = document.querySelector<HTMLAnchorElement>('a.flutuante')!
    expect(botao.textContent).toContain('Indicar alguém')
    expect(botao.getAttribute('href')).toBe('/indicacoes/nova')
  })

  it('a gestão vê "2 indicações com aviso da vizinhança" e o toque filtra com com_aviso=1', async () => {
    const chamadas = apiIndicacoes(ADMIN, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: 2 }),
      'GET /api/indicacoes?com_aviso=true': json(200, {
        itens: [resumo(9, { nome: 'Com aviso', avisos_abertos: 1, recomendam: 0 })],
        com_aviso: 2,
      }),
    })
    abrir('/indicacoes')
    const filtro = await screen.findByRole('button', { name: '2 indicações com aviso da vizinhança' })
    expect(filtro.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(filtro)
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/indicacoes?com_aviso=true')).toBe(true),
    )
    expect(await screen.findByText('Com aviso')).toBeTruthy()
    expect(screen.getByRole('button', { name: '2 indicações com aviso da vizinhança' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('uma indicação com aviso, no singular; zero não mostra nada', async () => {
    apiIndicacoes(ADMIN, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: 1 }) })
    abrir('/indicacoes')
    expect(await screen.findByRole('button', { name: '1 indicação com aviso da vizinhança' })).toBeTruthy()
    cleanup()
    apiIndicacoes(ADMIN, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: 0 }) })
    abrir('/indicacoes')
    await screen.findByText('Marcenaria Silva')
    expect(screen.queryByText(/com aviso da vizinhança/)).toBeNull()
  })

  it('o morador não vê a faixa da gestão', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }) })
    abrir('/indicacoes')
    await screen.findByText('Marcenaria Silva')
    expect(screen.queryByText(/com aviso da vizinhança/)).toBeNull()
  })

  it('o filtro mora no endereço: abrir com ?categoria=5 já filtra', async () => {
    const chamadas = apiIndicacoes(MORADOR, {
      'GET /api/indicacoes?categoria=5': json(200, { itens: [ITENS[1]], com_aviso: null }),
    })
    abrir('/indicacoes?categoria=5')
    expect(await screen.findByText('Fios & Cia')).toBeTruthy()
    expect(chamadas.some((c) => c.caminho === '/api/indicacoes?categoria=5')).toBe(true)
  })
})

describe('lista de indicações · revisão', () => {
  it('os cartões são h2 (o h1 é o título da tela)', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }) })
    abrir('/indicacoes')
    expect(await screen.findByRole('heading', { level: 2, name: 'Marcenaria Silva' })).toBeTruthy()
    expect(screen.queryAllByRole('heading', { level: 3 })).toHaveLength(0)
  })

  it('o trecho diz o lado: 👍 "Recomenda:" ou 👎 "Não recomenda:"', async () => {
    const contra = resumo(8, {
      nome: 'Pinta Rápido',
      recomendam: 0,
      nao_recomendam: 1,
      trecho: {
        unidade: { login: '1101', bloco: 1, apartamento: '101' },
        recomenda: false,
        comentario: 'Sujou tudo.',
        em: '2026-10-15T15:00:00Z',
      },
    })
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: [ITENS[0], contra], com_aviso: null }),
    })
    abrir('/indicacoes')
    const a_favor = await screen.findByRole('link', { name: /Marcenaria Silva/ })
    expect(a_favor.querySelector('.ind-trecho-texto')?.textContent).toBe('👍 Recomenda: “Caprichoso e pontual.”')
    const contra_ = screen.getByRole('link', { name: /Pinta Rápido/ })
    expect(contra_.querySelector('.ind-trecho-texto')?.textContent).toBe('👎 Não recomenda: “Sujou tudo.”')
  })

  it('zero recomendações não aparece verde com 👍; sem opinião nenhuma, o texto neutro', async () => {
    apiIndicacoes(ADMIN, {
      'GET /api/indicacoes': json(200, {
        itens: [
          resumo(8, { nome: 'Só contra', recomendam: 0, nao_recomendam: 2 }),
          resumo(9, { nome: 'Sem opinião', recomendam: 0, nao_recomendam: 0 }),
        ],
        com_aviso: null,
      }),
    })
    abrir('/indicacoes')
    const contra = await screen.findByRole('link', { name: /Só contra/ })
    expect(contra.querySelector('.ind-recomendam')).toBeNull()
    expect(contra.textContent).not.toContain('👍')
    expect(contra.querySelector('.ind-nao-recomendam')?.textContent).toBe('2 não recomendam')
    const sem = screen.getByRole('link', { name: /Sem opinião/ })
    expect(sem.querySelector('.ind-recomendam')).toBeNull()
    expect(sem.querySelector('.ind-sem-opiniao')?.textContent).toBe('Nenhum vizinho recomenda ainda')
  })

  it('com o filtro "com aviso" ligado e zero, o botão continua (é por ele que se desliga)', async () => {
    apiIndicacoes(ADMIN, {
      'GET /api/indicacoes?com_aviso=true': json(200, { itens: [], com_aviso: 0 }),
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: 0 }),
    })
    const roteador = abrir('/indicacoes?com_aviso=1')
    const filtro = await screen.findByRole('button', { name: '0 indicações com aviso da vizinhança' })
    expect(filtro.getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(filtro)
    await waitFor(() => expect(roteador.state.location.search).toBe(''))
    expect(await screen.findByText('Marcenaria Silva')).toBeTruthy()
  })

  it('"Todos" tira também o filtro "com aviso"', async () => {
    apiIndicacoes(ADMIN, {
      'GET /api/indicacoes?com_aviso=true': json(200, { itens: [ITENS[1]], com_aviso: 1 }),
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: 1 }),
    })
    const roteador = abrir('/indicacoes?com_aviso=1')
    const faixa = await screen.findByRole('navigation', { name: 'Categorias' })
    const todos = within(faixa).getByRole('button', { name: 'Todos' })
    expect(todos.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(todos)
    await waitFor(() => expect(roteador.state.location.search).toBe(''))
    expect(await screen.findByText('Marcenaria Silva')).toBeTruthy()
  })

  it('busca sem resultado oferece "Limpar a busca"', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }),
      'GET /api/indicacoes?busca=zzz': json(200, { itens: [], com_aviso: null }),
    })
    abrir('/indicacoes?busca=zzz')
    const limpar = await screen.findByRole('button', { name: 'Limpar a busca' })
    fireEvent.click(limpar)
    expect((screen.getByLabelText(/Procurar: nome ou serviço/) as HTMLInputElement).value).toBe('')
    expect(document.activeElement).toBe(screen.getByLabelText(/Procurar: nome ou serviço/))
    expect(await screen.findByText('Marcenaria Silva', {}, { timeout: 2000 })).toBeTruthy()
  })

  it('categoria sem resultado oferece "Ver todas" e "Indicar alguém"', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }),
      'GET /api/indicacoes?categoria=2': json(200, { itens: [], com_aviso: null }),
    })
    const roteador = abrir('/indicacoes?categoria=2')
    const ver = await screen.findByRole('button', { name: 'Ver todas' })
    const vazio = ver.closest('.ind-vazio') as HTMLElement
    expect(within(vazio).getByRole('link', { name: /Indicar alguém/ }).getAttribute('href')).toBe(
      '/indicacoes/nova',
    )
    fireEvent.click(ver)
    await waitFor(() => expect(roteador.state.location.search).toBe(''))
    expect(await screen.findByText('Marcenaria Silva')).toBeTruthy()
  })

  it('o anúncio do leitor de tela fala a contagem também ao trocar de categoria', async () => {
    apiIndicacoes(MORADOR, {
      'GET /api/indicacoes': json(200, { itens: ITENS, com_aviso: null }),
      'GET /api/indicacoes?categoria=5': json(200, { itens: [ITENS[1]], com_aviso: null }),
    })
    abrir('/indicacoes')
    const faixa = await screen.findByRole('navigation', { name: 'Categorias' })
    const anuncio = document.querySelector('.ind-busca [aria-live]')!
    expect(anuncio.textContent).toBe('')
    fireEvent.click(within(faixa).getByRole('button', { name: 'Eletricista' }))
    await waitFor(() => expect(anuncio.textContent).toBe('1 indicação encontrada.'))
  })
})

describe('menu', () => {
  it('o lugar Indicações aparece na folha do Menu e no menu lateral', async () => {
    apiIndicacoes(MORADOR, { 'GET /api/indicacoes': json(200, { itens: [], com_aviso: null }) })
    abrir('/avisos')
    const lateral = await waitFor(() => {
      const nav = document.querySelector<HTMLElement>('.nav-lateral')
      expect(nav).not.toBeNull()
      return nav!
    })
    const noLateral = within(lateral).getByRole('link', { name: /Indicações/ })
    expect(noLateral.getAttribute('href')).toBe('/indicacoes')
    const bola = within(document.querySelector<HTMLElement>('.nav-barra')!).getByRole('button', {
      name: 'Menu',
    })
    await act(async () => fireEvent.click(bola))
    const folha = await screen.findByRole('dialog', { name: 'Para onde você quer ir?' })
    const naFolha = within(folha).getByRole('link', { name: /Indicações/ })
    expect(naFolha.textContent).toContain('Serviços que os vizinhos recomendam')
    // Fora da barra.
    expect(within(document.querySelector<HTMLElement>('.nav-barra')!).queryByText('Indicações')).toBeNull()
  })
})
