// Classificados · a lista (spec, seção 3.1), "Meus anúncios" e o lugar novo no menu (seção 3.4),
// com a API de mentira e o Portal inteiro montado.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { apiClassificados, CAPA, resumo } from './apoioDeTeste'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MORADOR = eu()
const ADMIN = eu(['admin'], false, '1101')

const ITENS = [
  resumo(3, { titulo: 'Sofá de 3 lugares', capa: CAPA }),
  resumo(5, {
    titulo: 'Sobra de porcelanato',
    tipo: 'doacao',
    preco_centavos: null,
    categoria: { id: 4, nome: 'Material de obra e acabamento' },
    situacao: 'reservado',
  }),
  resumo(6, { titulo: 'Geladeira', preco_centavos: null }),
]

function lista(itens = ITENS, extra: object = {}) {
  return json(200, { itens, com_aviso: null, meus: 0, meus_abertos: 0, ...extra })
}

describe('lista de classificados', () => {
  it('mostra os cartões na ordem da API, com o selo, a capa, a placa e o reservado', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    const cartoes = await screen.findAllByRole('link', { name: /Sofá|porcelanato|Geladeira/ })
    expect(cartoes.map((c) => c.getAttribute('href'))).toEqual([
      '/classificados/3',
      '/classificados/5',
      '/classificados/6',
    ])
    expect(cartoes[0].textContent).toContain('Vende R$\u00a0350')
    expect(cartoes[0].textContent).toContain('Móveis')
    expect(cartoes[0].textContent).toContain('hoje')
    expect(cartoes[0].querySelector('img')?.getAttribute('src')).toBe(CAPA)
    expect(within(cartoes[0]).getByRole('img', { name: 'Bloco 2, apartamento 304' })).toBeTruthy()
    expect(cartoes[1].textContent).toContain('Doa')
    expect(cartoes[1].textContent).toContain('Reservado')
    expect(cartoes[1].querySelector('img')).toBeNull()
    expect(cartoes[2].textContent).toContain('Vende\u00a0· a\u00a0combinar')
    expect(screen.getByRole('heading', { level: 1, name: 'Classificados' })).toBeTruthy()
    // O botão de anunciar, fixo embaixo.
    expect(screen.getByRole('link', { name: /Anunciar/ }).getAttribute('href')).toBe(
      '/classificados/novo',
    )
  })

  it('o filtro de tipo e a faixa de categorias vão para a API e marcam aria-pressed', async () => {
    const chamadas = apiClassificados(MORADOR, {
      'GET /api/classificados': lista(),
      'GET /api/classificados?tipo=doacao': lista([ITENS[1]]),
      'GET /api/classificados?tipo=doacao&categoria=4': lista([ITENS[1]]),
    })
    abrir('/classificados')
    const tipos = await screen.findByRole('group', { name: 'O que você procura' }, { timeout: 4000 })
    expect(within(tipos).getAllByRole('button').map((b) => b.textContent)).toEqual([
      'Tudo',
      'Vende',
      'Troca',
      'Doa',
    ])
    expect(within(tipos).getByRole('button', { name: 'Tudo' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(within(tipos).getByRole('button', { name: 'Doa' }))
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/classificados?tipo=doacao')).toBe(true),
    )
    const faixa = screen.getByRole('navigation', { name: 'Categorias' })
    expect(within(faixa).getAllByRole('button')[0].textContent).toBe('Todas')
    fireEvent.click(within(faixa).getByRole('button', { name: 'Material de obra e acabamento' }))
    await waitFor(() =>
      expect(
        chamadas.some((c) => c.caminho === '/api/classificados?tipo=doacao&categoria=4'),
      ).toBe(true),
    )
    expect(within(tipos).getByRole('button', { name: 'Doa' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('a busca chama a API com ?busca= depois de digitar', async () => {
    const chamadas = apiClassificados(MORADOR, {
      'GET /api/classificados': lista(),
      'GET /api/classificados?busca=sofa': lista([ITENS[0]]),
    })
    abrir('/classificados')
    const campo = await screen.findByLabelText(/Procurar: o que você quer\?/)
    fireEvent.change(campo, { target: { value: 'sofa' } })
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/classificados?busca=sofa')).toBe(true),
    )
  })

  it('lista vazia mostra o convite e o botão de anunciar', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista([]) })
    abrir('/classificados')
    expect(
      await screen.findByText('Ainda não tem anúncio aqui. Que tal anunciar o que sobrou da obra?'),
    ).toBeTruthy()
    expect(screen.getAllByRole('link', { name: /Anunciar/ }).length).toBeGreaterThan(0)
  })

  it('busca sem resultado diz "Nenhum anúncio encontrado." e oferece limpar', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados': lista(),
      'GET /api/classificados?busca=piano': lista([]),
    })
    abrir('/classificados')
    fireEvent.change(await screen.findByLabelText(/Procurar/), { target: { value: 'piano' } })
    expect(await screen.findByText('Nenhum anúncio encontrado.', { selector: '.vazio' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Limpar a busca' }))
    expect((screen.getByLabelText(/Procurar/) as HTMLInputElement).value).toBe('')
  })

  it('"Meus anúncios" aparece no topo só quando a unidade tem algum', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista(ITENS, { meus: 3, meus_abertos: 2 }) })
    abrir('/classificados')
    const meus = await screen.findByRole('link', { name: /Meus anúncios/ })
    expect(meus.getAttribute('href')).toBe('/classificados/meus')
    expect(meus.textContent).toContain('2')
    cleanup()
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    await screen.findAllByRole('link', { name: /Sofá/ })
    expect(screen.queryByRole('link', { name: /Meus anúncios/ })).toBeNull()
  })

  it('a gestão vê "2 anúncios com aviso da vizinhança" e o toque filtra; o morador não vê', async () => {
    const chamadas = apiClassificados(ADMIN, {
      'GET /api/classificados': lista(ITENS, { com_aviso: 2 }),
      'GET /api/classificados?com_aviso=true': lista([ITENS[0]], { com_aviso: 2 }),
    })
    abrir('/classificados')
    const botao = await screen.findByRole('button', { name: /2 anúncios com aviso da vizinhança/ })
    fireEvent.click(botao)
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/classificados?com_aviso=true')).toBe(true),
    )
    cleanup()
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    await screen.findAllByRole('link', { name: /Sofá/ })
    expect(screen.queryByRole('button', { name: /com aviso da vizinhança/ })).toBeNull()
  })

  it('o lugar Classificados aparece no menu lateral', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    const links = await screen.findAllByRole('link', { name: /Classificados/ })
    expect(links.some((l) => l.getAttribute('href') === '/classificados')).toBe(true)
  })
})

describe('revisão de UX', () => {
  afterEach(() => {
    delete document.documentElement.dataset.letra
  })

  it('4: a faixa de tipo quebra em linha (as quatro à vista); a das categorias é que rola', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    const tipos = await screen.findByRole('group', { name: 'O que você procura' }, { timeout: 4000 })
    expect(tipos.classList.contains('faixa-categorias')).toBe(false)
    expect(tipos.classList.contains('cla-tipos')).toBe(true)
    // As categorias chegam num pedido à parte: espera por elas.
    const faixa = await screen.findByRole('navigation', { name: 'Categorias' }, { timeout: 4000 })
    expect(faixa.classList.contains('faixa-categorias')).toBe(true)
  })

  it('10: com a letra grande, "Anunciar" entra no fluxo, antes da busca; sem o flutuante', async () => {
    document.documentElement.dataset.letra = 'grande'
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    const busca = await screen.findByLabelText(/Procurar/, {}, { timeout: 4000 })
    const anunciar = screen.getAllByRole('link', { name: /Anunciar/ })
    expect(anunciar).toHaveLength(1)
    expect(anunciar[0].classList.contains('flutuante')).toBe(false)
    expect(anunciar[0].compareDocumentPosition(busca) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('10: com a letra de fábrica, continua o flutuante', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    await screen.findByLabelText(/Procurar/)
    expect(screen.getByRole('link', { name: /Anunciar/ }).classList.contains('flutuante')).toBe(true)
  })

  it('12: "Meus anúncios" sem número quando nenhum está aberto', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista(ITENS, { meus: 2, meus_abertos: 0 }) })
    abrir('/classificados')
    const meus = await screen.findByRole('link', { name: /Meus anúncios/ })
    expect(meus.textContent?.trim()).toBe('Meus anúncios')
  })

  it('12: em "Meus anúncios", o aberto diz até quando fica na lista', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/meus': json(200, {
        itens: [resumo(1, { titulo: 'Aberto', vence_em: '2026-11-19T15:00:00Z' })],
        limite: null,
      }),
    })
    abrir('/classificados/meus')
    const cartao = await screen.findByRole('link', { name: /Aberto/ })
    expect(cartao.textContent).toContain('Fica na lista até 19 de novembro')
  })
})

describe('meus anúncios', () => {
  it('lista os da unidade com o estado de cada um', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados/meus': json(200, {
        itens: [
          resumo(1, { titulo: 'Aberto' }),
          resumo(2, { titulo: 'Vencido', vencido: true }),
          resumo(3, { titulo: 'Encerrado', situacao: 'encerrado' }),
          resumo(4, { titulo: 'Escondido', escondido: true }),
        ],
      }),
    })
    abrir('/classificados/meus')
    const cartoes = await screen.findAllByRole('link', { name: /Aberto|Vencido|Encerrado|Escondido/ })
    expect(cartoes).toHaveLength(4)
    expect(cartoes[1].textContent).toContain('Vencido')
    expect(cartoes[2].textContent).toContain('Encerrado')
    expect(cartoes[3].textContent).toContain('Escondido pela gestão')
    expect(screen.getByRole('heading', { level: 1, name: 'Meus anúncios' })).toBeTruthy()
  })

  it('sem nenhum, convida a anunciar', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados/meus': json(200, { itens: [] }) })
    abrir('/classificados/meus')
    expect(await screen.findByText(/Você ainda não anunciou nada/)).toBeTruthy()
  })
})
