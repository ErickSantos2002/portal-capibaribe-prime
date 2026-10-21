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

  it('"Tipo" e "Categoria" são listas de escolher com rótulo, uma embaixo da outra', async () => {
    apiClassificados(MORADOR, { 'GET /api/classificados': lista() })
    abrir('/classificados')
    const tipo = (await screen.findByLabelText('Tipo', {}, { timeout: 4000 })) as HTMLSelectElement
    const categoria = (await screen.findByLabelText('Categoria', {}, { timeout: 4000 })) as HTMLSelectElement
    expect(tipo.tagName).toBe('SELECT')
    expect(categoria.tagName).toBe('SELECT')
    // <label for> de verdade, não aria-label.
    expect(document.querySelector(`label[for="${tipo.id}"]`)?.textContent).toBe('Tipo')
    expect(document.querySelector(`label[for="${categoria.id}"]`)?.textContent).toBe('Categoria')
    expect([...tipo.options].map((o) => o.textContent)).toEqual(['Tudo', 'Vende', 'Troca', 'Doa', 'Procura'])
    expect([...categoria.options].map((o) => o.textContent)).toEqual([
      'Todas',
      'Móveis',
      'Eletrodomésticos',
      'Material de obra e acabamento',
      'Outros',
    ])
    expect(tipo.selectedOptions[0].textContent).toBe('Tudo')
    expect(categoria.selectedOptions[0].textContent).toBe('Todas')
    // Uma embaixo da outra: o tipo vem antes da categoria.
    expect(tipo.compareDocumentPosition(categoria) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    // Nada de chips nem de faixa que rola.
    expect(document.querySelector('.faixa-categorias, .cla-tipos')).toBeNull()
  })

  it('escolher o tipo e depois a categoria vai para a API e para o endereço', async () => {
    const chamadas = apiClassificados(MORADOR, {
      'GET /api/classificados': lista(),
      'GET /api/classificados?tipo=doacao': lista([ITENS[1]]),
      'GET /api/classificados?tipo=doacao&categoria=4': lista([ITENS[1]]),
    })
    const roteador = abrir('/classificados')
    const tipo = (await screen.findByLabelText('Tipo', {}, { timeout: 4000 })) as HTMLSelectElement
    fireEvent.change(tipo, { target: { value: 'doacao' } })
    await waitFor(() =>
      expect(chamadas.some((c) => c.caminho === '/api/classificados?tipo=doacao')).toBe(true),
    )
    expect(roteador.state.location.search).toBe('?tipo=doacao')
    const categoria = (await screen.findByLabelText('Categoria', {}, { timeout: 4000 })) as HTMLSelectElement
    fireEvent.change(categoria, { target: { value: '4' } })
    await waitFor(() =>
      expect(
        chamadas.some((c) => c.caminho === '/api/classificados?tipo=doacao&categoria=4'),
      ).toBe(true),
    )
    expect(roteador.state.location.search).toBe('?tipo=doacao&categoria=4')
    expect(tipo.selectedOptions[0].textContent).toBe('Doa')
    expect(categoria.selectedOptions[0].textContent).toBe('Material de obra e acabamento')
    // "Tudo" e "Todas" tiram a chave do endereço.
    fireEvent.change(tipo, { target: { value: '' } })
    await waitFor(() => expect(roteador.state.location.search).toBe('?categoria=4'))
    fireEvent.change(categoria, { target: { value: '' } })
    await waitFor(() => expect(roteador.state.location.search).toBe(''))
  })

  it('o filtro que veio no endereço aparece escolhido nas listas', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados?tipo=procura&categoria=2': lista([ITENS[0]]),
    })
    abrir('/classificados?tipo=procura&categoria=2')
    const tipo = (await screen.findByLabelText('Tipo', {}, { timeout: 4000 })) as HTMLSelectElement
    const categoria = (await screen.findByLabelText('Categoria', {}, { timeout: 4000 })) as HTMLSelectElement
    expect(tipo.selectedOptions[0].textContent).toBe('Procura')
    await waitFor(() => expect(categoria.selectedOptions[0].textContent).toBe('Eletrodomésticos'))
  })

  it('tipo, categoria e busca juntos vão na mesma consulta', async () => {
    const chamadas = apiClassificados(MORADOR, {
      'GET /api/classificados?tipo=venda&categoria=1': lista([ITENS[0]]),
      'GET /api/classificados?tipo=venda&categoria=1&busca=sofa': lista([ITENS[0]]),
    })
    abrir('/classificados?tipo=venda&categoria=1')
    fireEvent.change(await screen.findByLabelText(/Procurar/), { target: { value: 'sofa' } })
    await waitFor(() =>
      expect(
        chamadas.some((c) => c.caminho === '/api/classificados?tipo=venda&categoria=1&busca=sofa'),
      ).toBe(true),
    )
  })

  it('filtro sem resultado: "Ver todos" volta as listas para "Tudo" e "Todas"', async () => {
    apiClassificados(MORADOR, {
      'GET /api/classificados': lista(),
      'GET /api/classificados?tipo=troca&categoria=8': lista([]),
    })
    const roteador = abrir('/classificados?tipo=troca&categoria=8')
    fireEvent.click(await screen.findByRole('button', { name: 'Ver todos' }, { timeout: 4000 }))
    await waitFor(() => expect(roteador.state.location.search).toBe(''))
    expect(await screen.findByText('Sofá de 3 lugares')).toBeTruthy()
    expect((screen.getByLabelText('Tipo') as HTMLSelectElement).selectedOptions[0].textContent).toBe('Tudo')
    expect((screen.getByLabelText('Categoria') as HTMLSelectElement).selectedOptions[0].textContent).toBe(
      'Todas',
    )
  })

  it('com aviso ligado, as listas não mudam; ligar e desligar não mexe no tipo nem na categoria', async () => {
    apiClassificados(ADMIN, {
      'GET /api/classificados?tipo=venda': lista(ITENS, { com_aviso: 1 }),
      'GET /api/classificados?tipo=venda&com_aviso=true': lista([ITENS[0]], { com_aviso: 1 }),
    })
    const roteador = abrir('/classificados?tipo=venda')
    fireEvent.click(await screen.findByRole('button', { name: /1 anúncio com aviso da vizinhança/ }))
    await waitFor(() => expect(roteador.state.location.search).toBe('?tipo=venda&com_aviso=1'))
    expect((screen.getByLabelText('Tipo') as HTMLSelectElement).value).toBe('venda')
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
