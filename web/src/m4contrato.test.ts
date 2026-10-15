// Contrato do M4 no front (docs/superpowers/specs/m4-contrato.md, seção 4): as frases do
// histórico, as funções de API das enquetes, os endereços das telas e os pontos de encaixe
// ligados mas ainda sem mostrar nada.
import { cleanup, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { matchRoutes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from './acesso/apoioDeTeste'
import { oQueFez } from './administracao/frases'
import type { ItemHistorico } from './administracao/tipos'
import type { AvisoCompleto, EnqueteDoAviso as EnqueteDoAvisoTipo } from './avisos/tipos'
import { itensDoMenu } from './casca/menu'
import * as enquetes from './enquetes/api'
import * as caminhos from './enquetes/caminhos'
import type { NovaEnquete } from './enquetes/tipos'
import { rotas } from './rotas'

// Marcadores no lugar dos encaixes dos épicos (a fábrica roda antes dos imports acima).
vi.mock('./enquetes/votar/rotas', async () => {
  const { createElement } = await import('react')
  return { rotasVotar: [{ path: 'enquetes-votar-encaixe', element: createElement('p') }] }
})
vi.mock('./enquetes/gestao/rotas', async () => {
  const { createElement } = await import('react')
  return { rotasGestaoEnquetes: [{ path: 'enquetes-gestao-encaixe', element: createElement('p') }] }
})
vi.mock('./enquetes/votar/menu', () => ({
  itemEnquetes: () => ({ para: '/enquetes', icone: 'enquetes', texto: 'Enquetes' }),
}))
vi.mock('./enquetes/votar/EnqueteDoAviso', async () => {
  const { createElement } = await import('react')
  return {
    EnqueteDoAviso: ({ enquete }: { enquete: EnqueteDoAvisoTipo | null }) =>
      enquete && createElement('p', null, `encaixe: enquete ${enquete.id} ${enquete.pergunta}`),
  }
})

describe('histórico do M4 em frases (H-11)', () => {
  const base: ItemHistorico = {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    acao: 'enquete_criada',
    entidade: 'enquete',
    entidade_id: 7,
    unidade_afetada: null,
    aviso_titulo: null,
    detalhes: { pergunta: 'Qual o melhor dia?', opcoes: 3 },
  }

  it('criar e editar enquete', () => {
    expect(oQueFez(base)).toBe('criou uma enquete')
    expect(oQueFez({ ...base, acao: 'enquete_editada' })).toBe('editou uma enquete')
  })
})

// --- funções de API ------------------------------------------------------------------------------

function espiar(status = 200, corpo: unknown = {}) {
  const fetch = vi.fn(
    async () =>
      new Response(JSON.stringify(corpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      }),
  )
  vi.stubGlobal('fetch', fetch)
  return fetch
}

function chamada(fetch: ReturnType<typeof espiar>, n = 0) {
  const [caminho, opcoes] = fetch.mock.calls[n] as unknown as [string, RequestInit]
  return {
    caminho,
    metodo: opcoes.method,
    corpo: opcoes.body ? JSON.parse(String(opcoes.body)) : undefined,
    cabecalhos: opcoes.headers,
  }
}

describe('enquetes/api', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lista, enquete e votantes são GET (épico B)', async () => {
    const fetch = espiar(200, { itens: [] })
    await enquetes.listarEnquetes()
    await enquetes.abrirEnquete(7)
    await enquetes.votantes(7)
    expect([0, 1, 2].map((n) => [chamada(fetch, n).metodo, chamada(fetch, n).caminho])).toEqual([
      ['GET', '/api/enquetes'],
      ['GET', '/api/enquetes/7'],
      ['GET', '/api/enquetes/7/votantes'],
    ])
  })

  it('votar e trocar o voto são o mesmo PUT, com X-Portal (épico B)', async () => {
    const fetch = espiar(200, {})
    await enquetes.votar(7, { opcoes: [21, 23] })
    expect(chamada(fetch)).toMatchObject({
      caminho: '/api/enquetes/7/voto',
      metodo: 'PUT',
      corpo: { opcoes: [21, 23] },
      cabecalhos: { 'X-Portal': '1' },
    })
  })

  it('criar é POST e editar é PUT (épico A)', async () => {
    const fetch = espiar(201, { id: 7, aviso_id: 40 })
    const nova: NovaEnquete = {
      pergunta: 'Qual o melhor dia?',
      opcoes: ['Terça', 'Quinta'],
      encerra_em: '2026-11-10T23:00:00Z',
      mostrar_resultado: 'so_no_fim',
      para_todos: false,
      blocos: [1, 2],
    }
    expect(await enquetes.criarEnquete(nova)).toEqual({ id: 7, aviso_id: 40 })
    // Revisão do épico A (pontos 2 e 9): na edição, tudo é obrigatório, com a base.
    const edicao = {
      pergunta: nova.pergunta,
      opcoes: nova.opcoes,
      multipla_escolha: false,
      encerra_em: nova.encerra_em,
      mostrar_resultado: 'so_no_fim' as const,
      editada_em_base: null,
    }
    await enquetes.editarEnquete(7, edicao)
    expect(chamada(fetch, 0)).toMatchObject({ caminho: '/api/enquetes', metodo: 'POST', corpo: nova })
    expect(chamada(fetch, 1)).toMatchObject({ caminho: '/api/enquetes/7', metodo: 'PUT', corpo: edicao })
  })
})

describe('enquetes/caminhos', () => {
  it('os endereços das telas dos dois épicos', () => {
    expect([
      caminhos.CAMINHO_ENQUETES,
      caminhos.CAMINHO_NOVA_ENQUETE,
      caminhos.caminhoEnquete(7),
      caminhos.caminhoVotantes(7),
      caminhos.caminhoEditarEnquete(7),
    ]).toEqual(['/enquetes', '/enquetes/nova', '/enquetes/7', '/enquetes/7/votantes', '/enquetes/7/editar'])
  })
})

// --- pontos de encaixe ---------------------------------------------------------------------------
// Os módulos dos épicos estão trocados por marcadores (vi.mock no topo): se a tela mostra o
// marcador, o encaixe está ligado. Os módulos de verdade vêm por `vi.importActual`.

describe('encaixes do M4 ligados', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('as rotas dos dois épicos entram nas rotas do Portal', () => {
    expect(matchRoutes(rotas, '/enquetes-votar-encaixe')?.at(-1)?.route.path).toBe('enquetes-votar-encaixe')
    expect(matchRoutes(rotas, '/enquetes-gestao-encaixe')?.at(-1)?.route.path).toBe('enquetes-gestao-encaixe')
  })

  it('o menu chama itemEnquetes, logo depois de Avisos', () => {
    expect(itensDoMenu(eu()).map((i) => i.texto)).toEqual(['Avisos', 'Enquetes', 'Documentos', 'Minha unidade'])
  })

  // Ajustes do M4, ponto 10: o cartão da enquete vem logo depois do título, antes do texto
  // (no celular, ele ficava abaixo da dobra).
  it('o aviso aberto passa a enquete que o gerou, antes do texto', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/avisos/7': json(200, avisoCompleto({
        id: 3,
        pergunta: 'Qual o melhor dia?',
        encerra_em: '2099-11-10T23:00:00Z',
        encerrada: false,
      })),
    })
    abrir('/avisos/7')
    const encaixe = await screen.findByText('encaixe: enquete 3 Qual o melhor dia?')
    const texto = screen.getByText('Texto do aviso')
    expect(encaixe.compareDocumentPosition(texto) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})

describe('encaixes do épico A mostram o que devem', () => {
  it('rotas de criar e editar enquete', async () => {
    const { rotasGestaoEnquetes } =
      await vi.importActual<typeof import('./enquetes/gestao/rotas')>('./enquetes/gestao/rotas')
    const caminhos: string[] = []
    const juntar = (rotas: typeof rotasGestaoEnquetes) =>
      rotas.forEach((r) => {
        if (r.path) caminhos.push(r.path)
        if (r.children) juntar(r.children)
      })
    juntar(rotasGestaoEnquetes)
    expect(caminhos).toEqual(['enquetes/nova', 'enquetes/:id/editar'])
  })
})

// Épicos A e B: a parte "ainda não mostram nada" virou estes blocos no merge do M4.
// O que cada encaixe mostra está em `enquetes/votar/votar.test.tsx`.
describe('encaixes do épico B mostram o que devem', () => {
  afterEach(cleanup)

  it('rotas de votar e item no menu para toda unidade', async () => {
    const { rotasVotar } = await vi.importActual<typeof import('./enquetes/votar/rotas')>('./enquetes/votar/rotas')
    const { itemEnquetes } = await vi.importActual<typeof import('./enquetes/votar/menu')>('./enquetes/votar/menu')
    expect(rotasVotar).not.toEqual([])
    expect(itemEnquetes(eu())?.para).toBe('/enquetes')
    expect(itemEnquetes(eu(['comissao']))?.para).toBe('/enquetes')
  })

  it('aviso sem enquete continua sem botão', async () => {
    const { EnqueteDoAviso } = await vi.importActual<typeof import('./enquetes/votar/EnqueteDoAviso')>(
      './enquetes/votar/EnqueteDoAviso',
    )
    expect(render(createElement(EnqueteDoAviso, { enquete: null })).container.innerHTML).toBe('')
  })
})

function avisoCompleto(enquete: EnqueteDoAvisoTipo | null): AvisoCompleto {
  return {
    id: 7,
    titulo: 'Enquete nova: Qual o melhor dia?',
    resumo: 'Texto do aviso',
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
    quantidade_anexos: 0,
    texto: 'Texto do aviso',
    evento: null,
    versoes_anteriores: [],
    leitura: null,
    anexos: [],
    documento: null,
    enquete,
  }
}
