// Telas do épico C com uma API de mentira: cada critério de aceite que aparece na tela.
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Eu, Papel } from '../api/tipos'
import { rotas } from '../rotas'
import type { AvisoCompleto, AvisoResumo } from './tipos'

function eu(papeis: Papel[] = []): Eu {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    papeis,
    gestao: papeis.length > 0,
    admin: papeis.includes('admin'),
    precisa_trocar_senha: false,
  }
}

function resumo(id: number, extra: Partial<AvisoResumo> = {}): AvisoResumo {
  return {
    id,
    titulo: `Aviso ${id}`,
    resumo: `Resumo ${id}`,
    publicado_em: '2026-11-03T12:00:00Z',
    publicado_por: 'Comissão',
    editado_em: null,
    fixado: false,
    para_todos: true,
    blocos: [],
    arquivado_em: null,
    lido: true,
    corrigido_desde_a_leitura: false,
    categoria: 'geral',
    evento_quando: null,
    ...extra,
  }
}

function completo(id: number, extra: Partial<AvisoCompleto> = {}): AvisoCompleto {
  return {
    ...resumo(id),
    texto: `Texto ${id}`,
    evento: null,
    versoes_anteriores: [],
    leitura: null,
    ...extra,
  }
}

function json(status: number, corpo: unknown) {
  return status === 204
    ? new Response(null, { status })
    : new Response(JSON.stringify(corpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
}

type Rota = (url: URL, init: RequestInit) => Response | undefined

/** API de mentira: `/api/acesso/eu` e `nao-lidos` prontos; o resto vem de `rota`. */
function api(sessao: Eu, rota: Rota) {
  const fetch = vi.fn(async (caminho: string, init: RequestInit = {}) => {
    const url = new URL(caminho, 'https://portal.test')
    if (url.pathname === '/api/acesso/eu') return json(200, sessao)
    if (url.pathname === '/api/avisos/nao-lidos') return json(200, { quantidade: 0 })
    return (
      rota(url, init) ?? json(404, { codigo: 'aviso_nao_encontrado', mensagem: 'Não achamos.' })
    )
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function chamadas(fetch: ReturnType<typeof api>, metodo: string, caminho: string) {
  return fetch.mock.calls.filter(([c, init]) => {
    const url = new URL(c, 'https://portal.test')
    return url.pathname === caminho && (init?.method ?? 'GET') === metodo
  })
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: [caminho] })
  render(<RouterProvider router={roteador} />)
  return roteador
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('mural (H-14)', () => {
  const itens = [
    resumo(1, { titulo: 'Bem-vindos', fixado: true, lido: false }),
    resumo(2, { titulo: 'Vistoria', lido: false, para_todos: false, blocos: [1, 2] }),
    resumo(3, { titulo: 'Reunião', editado_em: '2026-11-04T12:00:00Z' }),
  ]

  it('fixado no topo em destaque, depois a lista; não lido aparece como "Novo"', async () => {
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    const fixado = (await screen.findByText('Bem-vindos')).closest('a')!
    expect(fixado.classList.contains('fixado')).toBe(true)
    expect(within(fixado).getByText('Novo')).toBeTruthy()
    expect(within(fixado).getByText(/Fixado pela Comissão/)).toBeTruthy()
    expect(fixado.textContent).not.toContain('para os')

    const vistoria = screen.getByText('Vistoria').closest('a')!
    expect(vistoria.classList.contains('novo')).toBe(true)
    expect(within(vistoria).getByText('Novo')).toBeTruthy()
    expect(within(vistoria).getByText('Blocos 1 e 2')).toBeTruthy()
    expect(vistoria.getAttribute('href')).toBe('/avisos/2')

    const reuniao = screen.getByText('Reunião').closest('a')!
    expect(reuniao.classList.contains('novo')).toBe(false)
    expect(within(reuniao).getByText('corrigido em 4 de novembro')).toBeTruthy()
  })

  it('a busca pergunta à API com o que foi digitado', async () => {
    const fetch = api(eu(), (url) =>
      url.pathname === '/api/avisos'
        ? json(200, { itens: url.searchParams.get('busca') ? [itens[2]] : itens })
        : undefined,
    )
    abrir('/avisos')
    await screen.findByText('Vistoria')
    fireEvent.change(screen.getByLabelText('Procurar nos avisos'), {
      target: { value: 'reuniao' },
    })
    await waitFor(() => expect(screen.queryByText('Vistoria')).toBeNull())
    expect(screen.getByText('Reunião')).toBeTruthy()
    expect(screen.getByText('1 aviso encontrado.')).toBeTruthy()
    const ultima = new URL(fetch.mock.calls.at(-1)![0], 'https://portal.test')
    expect(ultima.searchParams.get('busca')).toBe('reuniao')
  })

  it('busca sem resultado diz o que fazer', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos'
        ? json(200, { itens: url.searchParams.get('busca') ? [] : itens })
        : undefined,
    )
    abrir('/avisos')
    await screen.findByText('Vistoria')
    fireEvent.change(screen.getByLabelText('Procurar nos avisos'), { target: { value: 'piscina' } })
    expect(
      await screen.findByText('Nenhum aviso com essas palavras. Tente outra palavra.'),
    ).toBeTruthy()
  })

  it('"Novo aviso" só para a gestão', async () => {
    api(eu(['comissao']), (url) =>
      url.pathname === '/api/avisos' ? json(200, { itens }) : undefined,
    )
    abrir('/avisos')
    expect(await screen.findByRole('link', { name: 'Novo aviso' })).toBeTruthy()
    cleanup()
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    await screen.findByText('Vistoria')
    expect(screen.queryByRole('link', { name: 'Novo aviso' })).toBeNull()
  })

  it('arquivados (H-15): lista própria, pedida com arquivados=true', async () => {
    const fetch = api(eu(), (url) =>
      url.pathname === '/api/avisos'
        ? json(200, {
            itens: [resumo(9, { titulo: 'Antigo', arquivado_em: '2026-11-05T12:00:00Z' })],
          })
        : undefined,
    )
    abrir('/avisos/arquivados')
    expect(await screen.findByRole('heading', { level: 1, name: 'Avisos arquivados' })).toBeTruthy()
    expect(await screen.findByText(/arquivado em 5 de novembro/)).toBeTruthy()
    const url = new URL(chamadas(fetch, 'GET', '/api/avisos')[0][0], 'https://portal.test')
    expect(url.searchParams.get('arquivados')).toBe('true')
  })
})

describe('aviso aberto', () => {
  it('texto puro: HTML aparece como texto, parágrafos e links seguros', async () => {
    const texto =
      '<b>negrito?</b> <img src=x onerror=alert(1)>\nlinha 2\n\nVeja https://exemplo.com.br/regras.'
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { texto })) : undefined,
    )
    abrir('/avisos/5')
    await screen.findByRole('heading', { level: 1, name: 'Aviso 5' })
    const artigo = document.querySelector('article')!
    expect(artigo.querySelector('b, img, script')).toBeNull()
    const paragrafos = artigo.querySelectorAll('.texto-aviso p')
    expect(paragrafos).toHaveLength(2)
    // A quebra simples virou `<br>` (spec dos avisos com formatação: sai o `pre-line`).
    expect(paragrafos[0].textContent).toBe('<b>negrito?</b> <img src=x onerror=alert(1)>linha 2')
    expect(paragrafos[0].querySelectorAll('br')).toHaveLength(1)
    const link = within(artigo).getByRole('link', { name: 'https://exemplo.com.br/regras' })
    expect(link.getAttribute('href')).toBe('https://exemplo.com.br/regras')
    expect(link.getAttribute('rel')).toBe('noopener noreferrer')
  })

  it('"Publicado pela Comissão" com a data e o destino (H-12)', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(200, completo(5, { para_todos: false, blocos: [4, 5] }))
        : undefined,
    )
    abrir('/avisos/5')
    expect(
      await screen.findByText('Publicado pela Comissão em 3 de novembro, para os Blocos 4 e 5.'),
    ).toBeTruthy()
  })

  it('abrir conta como lido (H-16): um POST só, e só se ainda não leu', async () => {
    const fetch = api(eu(), (url, init) => {
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { lido: false }))
      if (url.pathname === '/api/avisos/5/lido' && init.method === 'POST') return json(204, null)
    })
    abrir('/avisos/5')
    await screen.findByRole('heading', { level: 1, name: 'Aviso 5' })
    await waitFor(() => expect(chamadas(fetch, 'POST', '/api/avisos/5/lido')).toHaveLength(1))
    cleanup()
    const outro = api(eu(), (url) =>
      url.pathname === '/api/avisos/6' ? json(200, completo(6, { lido: true })) : undefined,
    )
    abrir('/avisos/6')
    await screen.findByRole('heading', { level: 1, name: 'Aviso 6' })
    expect(chamadas(outro, 'POST', '/api/avisos/6/lido')).toHaveLength(0)
  })

  it('corrigido mostra "Corrigido em" e a versão de antes, para todos (H-15)', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(
            200,
            completo(5, {
              editado_em: '2026-11-04T12:00:00Z',
              versoes_anteriores: [
                {
                  versao: 1,
                  titulo: 'Reunião às 19h',
                  texto: 'Antes.',
                  criada_em: '2026-11-03T12:00:00Z',
                  categoria: 'geral',
                  evento: null,
                },
              ],
            }),
          )
        : undefined,
    )
    abrir('/avisos/5')
    expect(await screen.findByText('Corrigido em 4 de novembro.')).toBeTruthy()
    expect(screen.getByText('Ver como era antes')).toBeTruthy()
    expect(screen.getByText('Reunião às 19h')).toBeTruthy()
    expect(screen.getByText('Antes.')).toBeTruthy()
  })

  it('aviso de outro bloco ou inexistente: "Não encontrado"', async () => {
    api(eu(), () => undefined)
    abrir('/avisos/5')
    expect(await screen.findByRole('heading', { name: 'Não encontrado' })).toBeTruthy()
  })

  it('unidade comum não vê ações de gestão', async () => {
    api(eu(), (url) => (url.pathname === '/api/avisos/5' ? json(200, completo(5)) : undefined))
    abrir('/avisos/5')
    await screen.findByRole('heading', { level: 1, name: 'Aviso 5' })
    expect(screen.queryByText(/Corrigir aviso/)).toBeNull()
    expect(screen.queryByText(/Arquivar/)).toBeNull()
  })

  it('gestão vê "X de Y leram", corrigir, fixar e arquivar; não existe apagar', async () => {
    api(eu(['comissao']), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(200, completo(5, { leitura: { lidos: 214, total: 320 } }))
        : undefined,
    )
    abrir('/avisos/5')
    const leitura = await screen.findByRole('link', { name: /214 de 320 apartamentos leram/ })
    expect(leitura.getAttribute('href')).toBe('/avisos/5/leitura')
    expect(screen.getByRole('link', { name: 'Corrigir aviso' }).getAttribute('href')).toBe(
      '/avisos/5/corrigir',
    )
    expect(screen.getByRole('button', { name: 'Fixar no topo do mural' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Arquivar' })).toBeTruthy()
    expect(screen.queryByText(/apagar|excluir/i)).toBeNull()
  })

  it('a seção de gestão se chama "Para a gestão" (o admin não é Comissão)', async () => {
    api(eu(['admin']), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(200, completo(5, { leitura: { lidos: 1, total: 320 } }))
        : undefined,
    )
    abrir('/avisos/5')
    expect(await screen.findByRole('heading', { level: 2, name: 'Para a gestão' })).toBeTruthy()
    expect(screen.queryByText('Para a Comissão')).toBeNull()
  })

  it('arquivar pede confirmação e depois mostra o aviso arquivado', async () => {
    const fetch = api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5')
        return json(200, completo(5, { leitura: { lidos: 1, total: 320 } }))
      if (url.pathname === '/api/avisos/5/arquivar' && init.method === 'POST') {
        return json(
          200,
          completo(5, { arquivado_em: '2026-11-06T12:00:00Z', leitura: { lidos: 1, total: 320 } }),
        )
      }
    })
    abrir('/avisos/5')
    fireEvent.click(await screen.findByRole('button', { name: 'Arquivar' }))
    expect(chamadas(fetch, 'POST', '/api/avisos/5/arquivar')).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Arquivar de vez' }))
    expect(await screen.findByText(/Arquivado em 6 de novembro/)).toBeTruthy()
    await waitFor(() =>
      expect(document.querySelector('.recado')?.textContent).toBe('Aviso arquivado.'),
    )
    expect(chamadas(fetch, 'POST', '/api/avisos/5/arquivar')).toHaveLength(1)
    expect(screen.queryByRole('link', { name: 'Corrigir aviso' })).toBeNull()
  })
})

describe('novo aviso (H-12)', () => {
  function apiDoFormulario() {
    return api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/destinos') {
        return json(200, { blocos: [1, 2, 3].map((n) => ({ numero: n, nome: `Bloco ${n}` })) })
      }
      if (url.pathname === '/api/avisos/alcance') {
        return json(200, { unidades: url.searchParams.getAll('blocos').length * 64 || 320 })
      }
      if (url.pathname === '/api/avisos' && init.method === 'POST') return json(201, completo(7))
      if (url.pathname === '/api/avisos') return json(200, { itens: [] })
    })
  }

  it('recusa sem título, marcando o campo', async () => {
    const fetch = apiDoFormulario()
    abrir('/avisos/novo')
    fireEvent.click(await screen.findByRole('button', { name: 'Ver prévia' }))
    const titulo = screen.getByLabelText('Título')
    expect(titulo.getAttribute('aria-invalid')).toBe('true')
    expect(screen.getAllByText('Escreva o título do aviso.').length).toBeGreaterThan(0)
    expect(chamadas(fetch, 'POST', '/api/avisos')).toHaveLength(0)
  })

  it('mostra quantos apartamentos recebem, a prévia, e só depois publica', async () => {
    const fetch = apiDoFormulario()
    const roteador = abrir('/avisos/novo')
    expect(await screen.findByText('320')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Vistoria' } })
    fireEvent.change(screen.getByLabelText('Texto do aviso'), {
      target: { value: 'Sábado.\n\nTraga documento.' },
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Bloco 2' }))
    fireEvent.click(screen.getByRole('button', { name: 'Bloco 3' }))
    expect(await screen.findByText('128')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: 'Todos os blocos' }).getAttribute('aria-pressed'),
    ).toBe('false')
    fireEvent.click(screen.getByLabelText('Fixar no topo do mural'))

    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    expect(await screen.findByText('Prévia: assim vai aparecer no mural')).toBeTruthy()
    expect(chamadas(fetch, 'POST', '/api/avisos')).toHaveLength(0)

    // Mexeu, a prévia some.
    fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Vistoria da obra' } })
    expect(screen.queryByText('Prévia: assim vai aparecer no mural')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar aviso' }))

    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
    // O recado chega à tela seguinte (a casca o lê do estado da navegação).
    await waitFor(() =>
      expect(document.querySelector('.recado')?.textContent).toBe('Aviso publicado.'),
    )
    const [, init] = chamadas(fetch, 'POST', '/api/avisos')[0]
    expect(JSON.parse(String(init?.body))).toEqual({
      titulo: 'Vistoria da obra',
      texto: 'Sábado.\n\nTraga documento.',
      para_todos: false,
      blocos: [2, 3],
      fixado: true,
      categoria: 'geral',
      evento: null,
    })
  })
})

describe('corrigir aviso (H-15)', () => {
  it('vem preenchido, manda a versão nova e volta ao aviso', async () => {
    const fetch = api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') return json(200, completo(5))
      if (url.pathname === '/api/avisos/5') return json(200, completo(5))
    })
    const roteador = abrir('/avisos/5/corrigir')
    const titulo = (await screen.findByLabelText('Título')) as HTMLInputElement
    expect(titulo.value).toBe('Aviso 5')
    fireEvent.change(titulo, { target: { value: 'Aviso 5, corrigido' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos/5'))
    await waitFor(() =>
      expect(document.querySelector('.recado')?.textContent).toBe('Aviso corrigido.'),
    )
    const [, init] = chamadas(fetch, 'PUT', '/api/avisos/5')[0]
    expect(JSON.parse(String(init?.body))).toEqual({
      titulo: 'Aviso 5, corrigido',
      texto: 'Texto 5',
      categoria: 'geral',
      evento: null,
    })
  })

  it('nada mudou: mostra a mensagem da API', async () => {
    api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') {
        return json(409, { codigo: 'sem_mudanca', mensagem: 'Nada mudou no aviso.' })
      }
      if (url.pathname === '/api/avisos/5') return json(200, completo(5))
    })
    abrir('/avisos/5/corrigir')
    fireEvent.click(await screen.findByRole('button', { name: 'Salvar correção' }))
    expect(await screen.findByText('Nada mudou no aviso.')).toBeTruthy()
  })
})

describe('quem leu (H-16)', () => {
  it('leram, ainda não, e os apartamentos por bloco', async () => {
    api(eu(['comissao']), (url) => {
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { titulo: 'Vistoria' }))
      if (url.pathname === '/api/avisos/5/leitura') {
        return json(200, {
          lidos: 125,
          total: 128,
          nao_entraram: [{ login: '3001', bloco: 3, apartamento: '001' }],
          entraram_sem_ler: [
            { login: '1101', bloco: 1, apartamento: '101' },
            { login: '1102', bloco: 1, apartamento: '102' },
          ],
        })
      }
    })
    abrir('/avisos/5/leitura')
    expect(await screen.findByText(/125 leram/)).toBeTruthy()
    expect(screen.getByText(/3 ainda não/)).toBeTruthy()
    const bloco1 = screen.getByRole('heading', { name: 'Bloco 1' }).closest('section')!
    expect(within(bloco1).getByLabelText('Bloco 1, apartamento 102')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Bloco 3' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Copiar a lista' })).toBeTruthy()
  })
})

// --- revisão independente do M1 ----------------------------------------------------------------

describe('revisão do M1 · U1: data, correção e selo "Corrigido"', () => {
  it('o fixado mostra a data e "corrigido em", como os outros itens', async () => {
    const itens = [
      resumo(1, { titulo: 'Bem-vindos', fixado: true, editado_em: '2026-11-04T12:00:00Z' }),
    ]
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    const fixado = (await screen.findByText('Bem-vindos')).closest('a')!
    expect(within(fixado).getByText('3 de novembro')).toBeTruthy()
    expect(within(fixado).getByText('corrigido em 4 de novembro')).toBeTruthy()
  })

  it('quem leu a versão anterior vê "Corrigido", não "Novo"', async () => {
    const itens = [
      resumo(1, { titulo: 'Fixado', fixado: true, corrigido_desde_a_leitura: true }),
      resumo(2, { titulo: 'Comum', corrigido_desde_a_leitura: true }),
    ]
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    for (const titulo of ['Fixado', 'Comum']) {
      const item = (await screen.findByText(titulo)).closest('a')!
      expect(within(item).getByText('Corrigido')).toBeTruthy()
      expect(within(item).queryByText('Novo')).toBeNull()
    }
  })

  it('abrir um aviso corrigido desde a leitura grava a leitura de novo', async () => {
    const fetch = api(eu(), (url, init) => {
      if (url.pathname === '/api/avisos/5' && (init.method ?? 'GET') === 'GET') {
        return json(200, completo(5, { corrigido_desde_a_leitura: true }))
      }
      if (url.pathname === '/api/avisos/5/lido') return json(204, null)
    })
    abrir('/avisos/5')
    await screen.findByText('Texto 5')
    await waitFor(() => expect(chamadas(fetch, 'POST', '/api/avisos/5/lido')).toHaveLength(1))
  })
})

describe('revisão do M1 · U2: confirmação de arquivar', () => {
  it('rola para o meio da tela e leva o foco', async () => {
    const rolar = vi.fn()
    Element.prototype.scrollIntoView = rolar
    api(eu(['comissao']), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(200, completo(5, { leitura: { lidos: 1, total: 2 } }))
        : undefined,
    )
    abrir('/avisos/5')
    fireEvent.click(await screen.findByRole('button', { name: 'Arquivar' }))
    const grupo = screen.getByRole('group', { name: /sai do mural/ })
    await waitFor(() => expect(rolar).toHaveBeenCalled())
    expect(rolar.mock.contexts.at(-1)).toBe(grupo)
    expect(document.activeElement).toBe(grupo)
  })
})

describe('revisão do M1 · U9: títulos', () => {
  it('no mural, cada aviso é um título de nível 2 (depois do h1)', async () => {
    const itens = [resumo(1, { titulo: 'Fixado', fixado: true }), resumo(2, { titulo: 'Comum' })]
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    expect(await screen.findByRole('heading', { level: 2, name: 'Fixado' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Comum' })).toBeTruthy()
  })

  it('o aviso aberto tem o assunto no h1 e no título da aba', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5'
        ? json(200, completo(5, { titulo: 'Vistoria da obra' }))
        : undefined,
    )
    abrir('/avisos/5')
    expect(await screen.findByRole('heading', { level: 1, name: 'Vistoria da obra' })).toBeTruthy()
    await waitFor(() => expect(document.title).toBe('Vistoria da obra · Portal Capibaribe Prime'))
  })
})

describe('revisão do M1 · U5: quem leu', () => {
  function leitura() {
    return {
      lidos: 120,
      total: 128,
      nao_entraram: [
        { login: '1001', bloco: 1, apartamento: '001' },
        { login: '1701', bloco: 1, apartamento: '701' },
      ],
      entraram_sem_ler: [
        { login: '1101', bloco: 1, apartamento: '101' },
        { login: '1702', bloco: 1, apartamento: '702' },
      ],
    }
  }

  async function abrirQuemLeu() {
    api(eu(['comissao']), (url) => {
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { titulo: 'Vistoria' }))
      if (url.pathname === '/api/avisos/5/leitura') return json(200, leitura())
    })
    abrir('/avisos/5/leitura')
    await screen.findByRole('heading', { name: /Ainda não entrou no Portal/ })
  }

  it('separa quem não entrou de quem entrou e não leu', async () => {
    await abrirQuemLeu()
    const naoEntrou = screen
      .getByRole('heading', { name: /Ainda não entrou no Portal/ })
      .closest('section')!
    const naoLeu = screen
      .getByRole('heading', { name: /Entrou, mas não leu este aviso/ })
      .closest('section')!
    expect(within(naoEntrou).getByLabelText('Bloco 1, apartamento 001')).toBeTruthy()
    expect(within(naoEntrou).queryByLabelText('Bloco 1, apartamento 101')).toBeNull()
    expect(within(naoLeu).getByLabelText('Bloco 1, apartamento 101')).toBeTruthy()
  })

  it('mesma ordem da grade do admin: do 7º andar ao térreo', async () => {
    await abrirQuemLeu()
    const naoEntrou = screen
      .getByRole('heading', { name: /Ainda não entrou no Portal/ })
      .closest('section')!
    const ordem = within(naoEntrou)
      .getAllByLabelText(/^Bloco 1, apartamento/)
      .map((e) => e.textContent)
    expect(ordem).toEqual(['701', '001'])
  })

  it('"Copiar a lista" fica no topo, antes das listas', async () => {
    await abrirQuemLeu()
    const copiar = screen.getByRole('button', { name: 'Copiar a lista' })
    const primeiraLista = screen.getByRole('heading', { name: /Ainda não entrou no Portal/ })
    expect(
      copiar.compareDocumentPosition(primeiraLista) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('os números do resumo não parecem botões', async () => {
    await abrirQuemLeu()
    expect(document.querySelector('.resumo')).toBeNull()
    expect(screen.getByText(/120 leram/)).toBeTruthy()
  })
})

// --- avisos com formatação, categoria e evento (spec de 06/10/2026) ---------------------------

const FUTURO = '2099-10-10T12:00:00Z' // um sábado, 9h em Recife
const PASSADO = '2020-10-10T12:00:00Z' // também sábado

describe('mural modelo A: categoria, data em bloco e evento', () => {
  const itens = [
    resumo(1, { titulo: 'Bem-vindos', fixado: true, categoria: 'geral' }),
    resumo(2, {
      titulo: 'Vistoria',
      categoria: 'obra',
      resumo: 'A construtora liberou a visita.',
      evento_quando: FUTURO,
      publicado_em: '2026-10-04T12:00:00Z',
    }),
    resumo(3, { titulo: 'Assembleia', categoria: 'reuniao', evento_quando: PASSADO }),
    resumo(4, { titulo: 'Reajuste', categoria: 'financeiro' }),
    resumo(5, { titulo: 'Prazo da Caixa', categoria: 'urgente' }),
  ]

  async function abrirMural() {
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    return (await screen.findByText('Vistoria')).closest('a')!
  }

  it('cada aviso mostra a categoria com nome (nunca só a cor) e a classe da cor', async () => {
    const vistoria = await abrirMural()
    expect(vistoria.classList.contains('cat-obra')).toBe(true)
    expect(within(vistoria).getByText('Obra')).toBeTruthy()
    for (const [titulo, nome] of [
      ['Assembleia', 'Reunião'],
      ['Reajuste', 'Financeiro'],
      ['Prazo da Caixa', 'Urgente'],
    ]) {
      const item = screen.getByText(titulo).closest('a')!
      expect(within(item).getByText(nome)).toBeTruthy()
    }
    const fixado = screen.getByText('Bem-vindos').closest('a')!
    expect(fixado.classList.contains('fixado')).toBe(true)
    expect(within(fixado).getByText('Geral')).toBeTruthy()
  })

  it('data da publicação em bloco (dia e mês), lida por extenso pelo leitor de tela', async () => {
    const vistoria = await abrirMural()
    const bloco = vistoria.querySelector('.data-bloco')!
    expect(bloco.getAttribute('aria-hidden')).toBe('true')
    expect(bloco.textContent).toBe('04out')
    expect(within(vistoria).getByText('4 de outubro')).toBeTruthy()
  })

  it('resumo embaixo do título', async () => {
    const vistoria = await abrirMural()
    expect(within(vistoria).getByText('A construtora liberou a visita.')).toBeTruthy()
  })

  it('evento futuro mostra dia e hora; o que já passou mostra "Já aconteceu"', async () => {
    const vistoria = await abrirMural()
    expect(within(vistoria).getByText('Sáb, 10/10 · 9h')).toBeTruthy()
    const assembleia = screen.getByText('Assembleia').closest('a')!
    expect(within(assembleia).getByText('Sáb, 10/10 · Já aconteceu')).toBeTruthy()
    const reajuste = screen.getByText('Reajuste').closest('a')!
    expect(reajuste.querySelector('.linha-evento')).toBeNull()
  })
})

describe('aviso aberto: cabeçalho, quadro do evento e texto formatado', () => {
  const formatado = [
    'Olá, vizinhos! O importante **não se perde mais**.',
    '',
    '## Como entrar',
    'Cada apartamento tem **uma conta só**.',
    '',
    '- Ler os avisos',
    '- Ver só o seu bloco',
    '',
    '1. Escolha o bloco',
    '2. Digite o apartamento',
    '',
    '> Seu celular só é visto pela Comissão.',
  ].join('\n')

  function abrirAviso(extra: Partial<AvisoCompleto>) {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, extra)) : undefined,
    )
    abrir('/avisos/5')
    return screen.findByRole('heading', { level: 1, name: 'Aviso 5' })
  }

  it('categoria e data em bloco no cabeçalho', async () => {
    await abrirAviso({ categoria: 'obra' })
    const artigo = document.querySelector('article')!
    expect(artigo.classList.contains('cat-obra')).toBe(true)
    expect(within(artigo).getByText('Obra')).toBeTruthy()
    expect(artigo.querySelector('.data-bloco')?.textContent).toBe('03nov')
  })

  it('evento: quadro "Quando / Onde" logo depois do cabeçalho', async () => {
    await abrirAviso({ evento: { quando: FUTURO, onde: 'Stand de vendas' } })
    const quadro = document.querySelector('.aviso-evento') as HTMLElement
    expect(within(quadro).getByText('Quando')).toBeTruthy()
    expect(within(quadro).getByText('Sábado, 10 de outubro, 9h')).toBeTruthy()
    expect(within(quadro).getByText('Onde')).toBeTruthy()
    expect(within(quadro).getByText('Stand de vendas')).toBeTruthy()
    // Antes do texto.
    const texto = document.querySelector('.texto-aviso')!
    expect(quadro.compareDocumentPosition(texto) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('evento sem local: só "Quando"; evento passado avisa que já aconteceu', async () => {
    await abrirAviso({ evento: { quando: PASSADO, onde: null } })
    const quadro = document.querySelector('.aviso-evento') as HTMLElement
    expect(within(quadro).queryByText('Onde')).toBeNull()
    expect(within(quadro).getByText(/Já aconteceu/)).toBeTruthy()
  })

  it('sem evento: nenhum quadro', async () => {
    await abrirAviso({})
    expect(document.querySelector('.aviso-evento')).toBeNull()
  })

  it('texto formatado: seção h2, negrito, listas e destaque', async () => {
    await abrirAviso({ texto: formatado })
    const texto = document.querySelector('.texto-aviso') as HTMLElement
    expect(within(texto).getByRole('heading', { level: 2, name: 'Como entrar' })).toBeTruthy()
    expect([...texto.querySelectorAll('strong')].map((s) => s.textContent)).toEqual([
      'não se perde mais',
      'uma conta só',
    ])
    expect([...texto.querySelectorAll('ul > li')].map((li) => li.textContent)).toEqual([
      'Ler os avisos',
      'Ver só o seu bloco',
    ])
    expect(texto.querySelectorAll('ol > li')).toHaveLength(2)
    expect(texto.querySelector('.aviso-destaque')?.textContent).toBe(
      'Seu celular só é visto pela Comissão.',
    )
    expect(texto.textContent).not.toMatch(/\*\*|## |^- /m)
  })

  it('a versão antiga aparece formatada, com a categoria e o evento dela', async () => {
    await abrirAviso({
      categoria: 'urgente',
      editado_em: '2026-11-04T12:00:00Z',
      versoes_anteriores: [
        {
          versao: 1,
          titulo: 'Antes',
          texto: '## Seção antiga\n- item antigo',
          criada_em: '2026-11-03T12:00:00Z',
          categoria: 'reuniao',
          evento: { quando: FUTURO, onde: 'Salão' },
        },
      ],
    })
    const antiga = document.querySelector('.avisos-versao') as HTMLElement
    expect(within(antiga).getByText('Reunião')).toBeTruthy()
    expect(within(antiga).getByText('Salão')).toBeTruthy()
    // Dentro da versão antiga (cujo título é h2), a seção desce um nível.
    expect(within(antiga).getByRole('heading', { level: 3, name: 'Seção antiga' })).toBeTruthy()
    expect(within(antiga).getByText('item antigo').tagName).toBe('LI')
  })
})

describe('formulário: categoria, barra de marcas, "Ver como fica" e evento', () => {
  function apiDoFormulario(aviso?: AvisoCompleto) {
    return api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/destinos') {
        return json(200, { blocos: [1, 2].map((n) => ({ numero: n, nome: `Bloco ${n}` })) })
      }
      if (url.pathname === '/api/avisos/alcance') return json(200, { unidades: 320 })
      if (url.pathname === '/api/avisos' && init.method === 'POST') return json(201, completo(7))
      if (url.pathname === '/api/avisos') return json(200, { itens: [] })
      if (aviso && url.pathname === `/api/avisos/${aviso.id}`) return json(200, aviso)
    })
  }

  async function preencher() {
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Vistoria' } })
    fireEvent.change(screen.getByLabelText('Texto do aviso'), { target: { value: 'Sábado.' } })
  }

  async function publicarECorpo(fetch: ReturnType<typeof api>) {
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar aviso' }))
    await waitFor(() => expect(chamadas(fetch, 'POST', '/api/avisos')).toHaveLength(1))
    const [, init] = chamadas(fetch, 'POST', '/api/avisos')[0]
    return JSON.parse(String(init?.body))
  }

  it('categoria: 5 rádios de verdade (setas do teclado), Geral marcada', async () => {
    const fetch = apiDoFormulario()
    abrir('/avisos/novo')
    const grupo = await screen.findByRole('group', { name: 'Categoria' })
    const radios = within(grupo).getAllByRole('radio') as HTMLInputElement[]
    expect(radios.map((r) => r.labels?.[0]?.textContent)).toEqual([
      'Geral',
      'Obra',
      'Reunião',
      'Financeiro',
      'Urgente',
    ])
    // Mesmo `name`: o navegador move a escolha com as setas.
    expect(new Set(radios.map((r) => r.name)).size).toBe(1)
    expect(radios[0].checked).toBe(true)
    fireEvent.click(within(grupo).getByLabelText('Obra'))
    expect(radios[1].checked).toBe(true)
    await preencher()
    expect((await publicarECorpo(fetch)).categoria).toBe('obra')
  })

  it('a barra insere a marca na seleção e devolve o foco ao texto', async () => {
    apiDoFormulario()
    abrir('/avisos/novo')
    const texto = (await screen.findByLabelText('Texto do aviso')) as HTMLTextAreaElement
    fireEvent.change(texto, { target: { value: 'Leve documento' } })
    texto.setSelectionRange(5, 14)
    fireEvent.click(screen.getByRole('button', { name: 'Negrito' }))
    expect(texto.value).toBe('Leve **documento**')
    await waitFor(() => expect(document.activeElement).toBe(texto))
    expect(texto.value.slice(texto.selectionStart, texto.selectionEnd)).toBe('documento')

    texto.setSelectionRange(0, 0)
    fireEvent.click(screen.getByRole('button', { name: 'Lista' }))
    expect(texto.value).toBe('- Leve **documento**')
    fireEvent.click(screen.getByRole('button', { name: 'Destaque' }))
    expect(texto.value).toBe('> Leve **documento**')
    fireEvent.click(screen.getByRole('button', { name: 'Título' }))
    expect(texto.value).toBe('## Leve **documento**')
  })

  it('"Ver como fica" troca o campo pela prévia formatada, e volta', async () => {
    apiDoFormulario()
    abrir('/avisos/novo')
    fireEvent.change(await screen.findByLabelText('Texto do aviso'), {
      target: { value: '## Como entrar\n- Bloco\n- Apartamento' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ver como fica' }))
    expect(screen.queryByLabelText('Texto do aviso')).toBeNull()
    const previa = document.querySelector('.avisos-como-fica') as HTMLElement
    expect(within(previa).getByRole('heading', { name: 'Como entrar' })).toBeTruthy()
    expect(within(previa).getAllByRole('listitem')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Voltar a escrever' }))
    expect((screen.getByLabelText('Texto do aviso') as HTMLTextAreaElement).value).toBe(
      '## Como entrar\n- Bloco\n- Apartamento',
    )
  })

  it('"É um evento?" mostra dia, hora e local, e manda o evento no horário de Recife', async () => {
    const fetch = apiDoFormulario()
    abrir('/avisos/novo')
    await preencher()
    expect(screen.queryByLabelText('Dia')).toBeNull()
    fireEvent.click(screen.getByLabelText('É um evento? (reunião, vistoria, mutirão)'))
    fireEvent.change(screen.getByLabelText('Dia'), { target: { value: '2026-10-10' } })
    fireEvent.change(screen.getByLabelText('Hora'), { target: { value: '09:00' } })
    fireEvent.change(screen.getByLabelText('Onde (se quiser)'), {
      target: { value: ' Stand de vendas ' },
    })
    expect((await publicarECorpo(fetch)).evento).toEqual({
      quando: '2026-10-10T09:00:00-03:00',
      onde: 'Stand de vendas',
    })
  })

  it('evento sem dia ou hora: avisa antes de mandar', async () => {
    const fetch = apiDoFormulario()
    abrir('/avisos/novo')
    await preencher()
    fireEvent.click(screen.getByLabelText('É um evento? (reunião, vistoria, mutirão)'))
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    expect(screen.getAllByText('Escolha o dia e a hora do evento.').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Dia').getAttribute('aria-invalid')).toBe('true')
    expect(chamadas(fetch, 'POST', '/api/avisos')).toHaveLength(0)
  })

  it('a prévia de publicar mostra o aviso aberto com categoria e quadro do evento', async () => {
    apiDoFormulario()
    abrir('/avisos/novo')
    await preencher()
    fireEvent.click(screen.getByLabelText('Reunião'))
    fireEvent.click(screen.getByLabelText('É um evento? (reunião, vistoria, mutirão)'))
    fireEvent.change(screen.getByLabelText('Dia'), { target: { value: '2099-10-10' } })
    fireEvent.change(screen.getByLabelText('Hora'), { target: { value: '19:30' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    const previa = (await screen.findByText('Prévia: assim vai aparecer no mural')).closest(
      '.previa',
    ) as HTMLElement
    expect(within(previa).getAllByText('Reunião').length).toBe(2)
    expect(within(previa).getByText('Sáb, 10/10 · 19h30')).toBeTruthy()
    expect(within(previa).getByText('Sábado, 10 de outubro, 19h30')).toBeTruthy()
  })

  it('corrigir vem com a categoria e o evento da versão em vigor e manda os novos', async () => {
    const aviso = completo(5, {
      categoria: 'reuniao',
      evento: { quando: '2026-10-10T22:30:00Z', onde: 'Salão' },
    })
    const fetch = api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') return json(200, aviso)
      if (url.pathname === '/api/avisos/5') return json(200, aviso)
    })
    abrir('/avisos/5/corrigir')
    expect(((await screen.findByLabelText('Reunião')) as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('Dia') as HTMLInputElement).value).toBe('2026-10-10')
    expect((screen.getByLabelText('Hora') as HTMLInputElement).value).toBe('19:30')
    expect((screen.getByLabelText('Onde (se quiser)') as HTMLInputElement).value).toBe('Salão')
    fireEvent.click(screen.getByLabelText('Urgente'))
    fireEvent.click(screen.getByLabelText('É um evento? (reunião, vistoria, mutirão)'))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(chamadas(fetch, 'PUT', '/api/avisos/5')).toHaveLength(1))
    const [, init] = chamadas(fetch, 'PUT', '/api/avisos/5')[0]
    expect(JSON.parse(String(init?.body))).toEqual({
      titulo: 'Aviso 5',
      texto: 'Texto 5',
      categoria: 'urgente',
      evento: null,
    })
  })
})
