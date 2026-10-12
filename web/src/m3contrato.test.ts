// Contrato do M3 no front (docs/superpowers/specs/m3-contrato.md, seções 5 e 7): as frases do
// histórico, as funções de API dos documentos (épico A) e do anexo (épico B), e os pontos de
// encaixe ligados mas ainda sem mostrar nada.
import { cleanup, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { matchRoutes } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from './acesso/apoioDeTeste'
import { oQueFez } from './administracao/frases'
import type { ItemHistorico } from './administracao/tipos'
import * as avisos from './avisos/api'
import type { AvisoCompleto, DocumentoDoAviso as DocumentoDoAvisoTipo } from './avisos/tipos'
import { itensDoMenu } from './casca/menu'
import * as documentos from './documentos/api'
import { rotas } from './rotas'

// Marcadores no lugar dos encaixes do épico A (a fábrica roda antes dos imports acima).
vi.mock('./documentos/rotas', async () => {
  const { createElement } = await import('react')
  return { rotasDocumentos: [{ path: 'documentos-encaixe', element: createElement('p') }] }
})
vi.mock('./documentos/menu', () => ({
  itemDocumentos: () => ({ para: '/documentos', icone: 'documentos', texto: 'Documentos' }),
}))
vi.mock('./documentos/LinkDocumentosPublicos', async () => {
  const { createElement } = await import('react')
  return { LinkDocumentosPublicos: () => createElement('p', null, 'encaixe: documentos públicos') }
})
vi.mock('./documentos/DocumentoDoAviso', async () => {
  const { createElement } = await import('react')
  return {
    DocumentoDoAviso: ({ documento }: { documento: DocumentoDoAvisoTipo | null }) =>
      documento && createElement('p', null, `encaixe: documento ${documento.id} ${documento.titulo}`),
  }
})

describe('histórico do M3 em frases (H-11)', () => {
  const base: ItemHistorico = {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    acao: 'arquivo_recusado',
    entidade: 'arquivo',
    entidade_id: 7,
    unidade_afetada: null,
    aviso_titulo: null,
    detalhes: {
      motivo: 'conteudo',
      finalidade: 'documento',
      tipo_declarado: 'application/pdf',
      tipo_encontrado: null,
      tamanho_bytes: 1000,
    },
  }

  it('arquivo recusado: diz por quê, sem o nome do arquivo', () => {
    expect(oQueFez(base)).toBe('tentou enviar um arquivo que não era PDF nem foto (recusado)')
    expect(oQueFez({ ...base, detalhes: { ...base.detalhes, motivo: 'tamanho' } })).toBe(
      'tentou enviar um arquivo maior que o limite (recusado)',
    )
  })

  it('documentos: publicar, versão nova e arquivar', () => {
    const doc = { ...base, entidade: 'documento', detalhes: {} }
    expect(oQueFez({ ...doc, acao: 'documento_publicado' })).toBe('publicou um documento')
    expect(oQueFez({ ...doc, acao: 'documento_versao_enviada', detalhes: { versao: 3 } })).toBe(
      'enviou a versão 3 de um documento',
    )
    expect(oQueFez({ ...doc, acao: 'documento_versao_enviada' })).toBe(
      'enviou uma versão nova de um documento',
    )
    expect(oQueFez({ ...doc, acao: 'documento_arquivado' })).toBe('arquivou um documento')
  })
})

// --- funções de API (épico A e épico B) --------------------------------------------------------

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

describe('documentos/api (épico A)', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('lista, públicos e abrir são GET', async () => {
    const fetch = espiar(200, { itens: [] })
    await documentos.listarDocumentos()
    await documentos.listarDocumentos({ arquivados: true })
    await documentos.listarDocumentosPublicos()
    await documentos.abrirDocumento(7)
    expect([0, 1, 2, 3].map((n) => [chamada(fetch, n).metodo, chamada(fetch, n).caminho])).toEqual([
      ['GET', '/api/documentos'],
      ['GET', '/api/documentos?arquivados=true'],
      ['GET', '/api/documentos/publicos'],
      ['GET', '/api/documentos/7'],
    ])
  })

  it('publicar, nova versão e arquivar são POST com X-Portal', async () => {
    const fetch = espiar(201, {})
    const novo = {
      titulo: 'Ata de outubro',
      categoria: 'ata',
      data_documento: '2026-10-05',
      acesso: 'compradores',
      arquivo_id: 42,
      avisar_unidades: true,
    } as const
    await documentos.publicarDocumento(novo)
    await documentos.enviarNovaVersao(7, { arquivo_id: 43 })
    await documentos.arquivarDocumento(7)
    expect(chamada(fetch, 0)).toMatchObject({
      caminho: '/api/documentos',
      metodo: 'POST',
      corpo: novo,
      cabecalhos: { 'X-Portal': '1' },
    })
    expect(chamada(fetch, 1)).toMatchObject({
      caminho: '/api/documentos/7/versoes',
      metodo: 'POST',
      corpo: { arquivo_id: 43 },
    })
    expect(chamada(fetch, 2)).toMatchObject({
      caminho: '/api/documentos/7/arquivar',
      metodo: 'POST',
      corpo: undefined,
    })
  })

  it('link da versão: abrir ou baixar, pedido na hora', async () => {
    const fetch = espiar(200, { url: 'https://x', expira_em: '2026-11-03T12:05:00Z' })
    await documentos.linkDaVersao(7, 2)
    await documentos.linkDaVersao(7, 2, true)
    expect([chamada(fetch, 0).caminho, chamada(fetch, 1).caminho]).toEqual([
      '/api/documentos/7/versoes/2/link',
      '/api/documentos/7/versoes/2/link?baixar=true',
    ])
  })
})

describe('avisos/api: link do anexo (épico B)', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('GET no link do anexo do aviso, com baixar só quando pedido', async () => {
    const fetch = espiar(200, { url: 'https://x', expira_em: '2026-11-03T12:05:00Z' })
    await avisos.linkDoAnexo(3, 42)
    await avisos.linkDoAnexo(3, 42, true)
    expect(chamada(fetch, 0)).toMatchObject({ caminho: '/api/avisos/3/anexos/42/link', metodo: 'GET' })
    expect(chamada(fetch, 1).caminho).toBe('/api/avisos/3/anexos/42/link?baixar=true')
  })
})

// --- pontos de encaixe (seção 7) ---------------------------------------------------------------
// Os módulos do épico A estão trocados por marcadores (vi.mock no topo): se a tela mostra o
// marcador, o encaixe está ligado. Os módulos de verdade vêm por `vi.importActual`.

describe('encaixes do épico A ligados', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('as rotas do épico entram nas rotas do Portal', () => {
    expect(matchRoutes(rotas, '/documentos-encaixe')?.at(-1)?.route.path).toBe('documentos-encaixe')
  })

  it('o menu chama itemDocumentos, logo depois de Avisos', () => {
    expect(itensDoMenu(eu()).map((i) => i.texto)).toEqual(['Avisos', 'Documentos', 'Minha unidade'])
    expect(itensDoMenu(eu(['comissao'])).map((i) => i.para)).toEqual([
      '/avisos',
      '/documentos',
      '/minha-unidade',
      '/unidades',
    ])
  })

  it('a entrada mostra o link dos documentos públicos depois do "Esqueci minha senha"', async () => {
    apiFalsa({})
    abrir('/entrar')
    const encaixe = await screen.findByText('encaixe: documentos públicos')
    const esqueci = screen.getByRole('link', { name: 'Esqueci minha senha' })
    expect(esqueci.compareDocumentPosition(encaixe) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('o aviso aberto passa o documento que o gerou, depois do texto', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/avisos/7': json(200, avisoCompleto({ id: 7, titulo: 'Ata de outubro' })),
    })
    abrir('/avisos/7')
    const encaixe = await screen.findByText('encaixe: documento 7 Ata de outubro')
    const texto = screen.getByText('Texto do aviso')
    expect(texto.compareDocumentPosition(encaixe) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})

describe('encaixes do épico A ainda não mostram nada', () => {
  afterEach(cleanup)

  it('sem rotas e sem item no menu', async () => {
    const { rotasDocumentos } =
      await vi.importActual<typeof import('./documentos/rotas')>('./documentos/rotas')
    const { itemDocumentos } = await vi.importActual<typeof import('./documentos/menu')>('./documentos/menu')
    expect(rotasDocumentos).toEqual([])
    expect(itemDocumentos(eu())).toBeNull()
    expect(itemDocumentos(eu(['admin']))).toBeNull()
  })

  it('entrada sem link e aviso sem botão', async () => {
    const { LinkDocumentosPublicos } = await vi.importActual<
      typeof import('./documentos/LinkDocumentosPublicos')
    >('./documentos/LinkDocumentosPublicos')
    const { DocumentoDoAviso } = await vi.importActual<typeof import('./documentos/DocumentoDoAviso')>(
      './documentos/DocumentoDoAviso',
    )
    expect(render(createElement(LinkDocumentosPublicos)).container.innerHTML).toBe('')
    const documento = { id: 7, titulo: 'Ata de outubro' }
    expect(render(createElement(DocumentoDoAviso, { documento })).container.innerHTML).toBe('')
  })
})

function avisoCompleto(documento: DocumentoDoAvisoTipo | null): AvisoCompleto {
  return {
    id: 7,
    titulo: 'Documento novo: Ata de outubro',
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
    documento,
  }
}
