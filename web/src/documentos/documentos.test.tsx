// Épico A do M3 · telas dos documentos com uma API de mentira: cada critério de H-17, H-18 e
// H-19 que aparece na tela.
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import { DocumentoDoAviso } from './DocumentoDoAviso'
import { navegador } from './abrir'
import { itemDocumentos } from './menu'
import type { Documento, DocumentoResumo } from './tipos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function resumo(id: number, extra: Partial<DocumentoResumo> = {}): DocumentoResumo {
  return {
    id,
    titulo: `Documento ${id}`,
    categoria: 'obra',
    data_documento: '2026-10-01',
    acesso: 'compradores',
    versao: 1,
    atualizado_em: '2026-10-02T12:00:00Z',
    arquivo: { id: id * 10, nome: `doc-${id}.pdf`, tipo: 'application/pdf', tamanho_bytes: 2_516_582 },
    arquivado_em: null,
    ...extra,
  }
}

function documento(id: number, extra: Partial<Documento> = {}): Documento {
  return { ...resumo(id), versoes_anteriores: [], aviso_id: null, ...extra }
}

const LINK = { url: 'https://arquivos.falso/arquivos/abc?x=1', expira_em: '2026-10-02T12:05:00Z' }

function abaFalsa() {
  const aba = { opener: {} as unknown, location: { href: '' }, close: vi.fn() }
  vi.spyOn(navegador, 'abrirAba').mockReturnValue(aba as unknown as Window)
  return aba
}

// --- menu e encaixes ---------------------------------------------------------------------------

describe('encaixes', () => {
  it('o menu tem "Documentos" para toda unidade', () => {
    for (const quem of [eu(), eu(['comissao'])]) {
      expect(itemDocumentos(quem)).toEqual({
        para: '/documentos',
        icone: 'documentos',
        texto: 'Documentos',
      })
    }
  })

  it('o aviso automático leva ao documento', () => {
    render(
      createElement(
        MemoryRouter,
        null,
        createElement(DocumentoDoAviso, { documento: { id: 7, titulo: 'Regimento interno' } }),
      ),
    )
    const link = screen.getByRole('link', { name: /Abrir o documento.*Regimento interno/ })
    expect(link.getAttribute('href')).toBe('/documentos/7')
  })

  it('aviso sem documento não mostra nada', () => {
    const { container } = render(
      createElement(MemoryRouter, null, createElement(DocumentoDoAviso, { documento: null })),
    )
    expect(container.innerHTML).toBe('')
  })

  it('a entrada leva aos documentos públicos', async () => {
    apiFalsa({})
    abrir('/entrar')
    const link = await screen.findByRole('link', { name: 'Ver documentos públicos' })
    expect(link.getAttribute('href')).toBe('/documentos/publicos')
  })
})

// --- lista (H-18) ------------------------------------------------------------------------------

describe('lista de documentos', () => {
  const itens = [
    resumo(1, { titulo: 'Cronograma da obra', versao: 3 }),
    resumo(2, { titulo: 'Ata da reunião', categoria: 'ata', acesso: 'gestao' }),
    resumo(3, { titulo: 'Convenção do condomínio', categoria: 'convencao' }),
  ]

  it('agrupa por assunto, com a data e a versão, e cada item abre o documento', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos': json(200, { itens }),
    })
    abrir('/documentos')
    const obra = await screen.findByRole('heading', { name: 'Obra' })
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual([
      'Obra',
      'Convenção',
      'Atas',
    ])
    expect(obra).toBeTruthy()
    const item = screen.getByRole('link', { name: /Cronograma da obra/ })
    expect(item.getAttribute('href')).toBe('/documentos/1')
    expect(item.textContent).toContain('1 de outubro de 2026')
    expect(item.textContent).toContain('versão 3')
    expect(screen.queryByRole('link', { name: /Novo documento/ })).toBeNull()
  })

  it('o de nível gestão tem a marca "só a gestão vê"', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['comissao'])),
      'GET /api/documentos': json(200, { itens }),
    })
    abrir('/documentos')
    const ata = await screen.findByRole('link', { name: /Ata da reunião/ })
    expect(ata.textContent).toContain('só a gestão vê')
    expect(screen.getByRole('link', { name: /Cronograma/ }).textContent).not.toContain('gestão')
  })

  it('busca pelo título, sem acento, e diz quando não acha', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos': json(200, { itens }),
    })
    abrir('/documentos')
    const busca = await screen.findByLabelText('Procurar documento')
    fireEvent.change(busca, { target: { value: 'convencao' } })
    expect(screen.getAllByRole('link', { name: /Convenção|Cronograma|Ata/ })).toHaveLength(1)
    fireEvent.change(busca, { target: { value: 'piscina' } })
    expect(screen.getByText('Nenhum documento com essas palavras. Tente outra palavra.')).toBeTruthy()
  })

  it('para a gestão: "Novo documento" e os arquivados', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['comissao'])),
      'GET /api/documentos': json(200, { itens: [] }),
    })
    abrir('/documentos')
    expect((await screen.findByRole('link', { name: /Novo documento/ })).getAttribute('href')).toBe(
      '/documentos/novo',
    )
    expect(
      (await screen.findByRole('link', { name: /Ver os documentos arquivados/ })).getAttribute(
        'href',
      ),
    ).toBe('/documentos/arquivados')
    expect(screen.getByText('Nenhum documento publicado ainda.')).toBeTruthy()
  })

  it('os arquivados pedem ?arquivados=true', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['admin'])),
      'GET /api/documentos?arquivados=true': json(200, {
        itens: [resumo(4, { arquivado_em: '2026-10-05T12:00:00Z' })],
      }),
    })
    abrir('/documentos/arquivados')
    expect(await screen.findByRole('link', { name: /Documento 4/ })).toBeTruthy()
    expect(chamadas.some((c) => c.caminho === '/api/documentos?arquivados=true')).toBe(true)
  })

  it('a unidade comum não abre os arquivados', async () => {
    apiFalsa({ 'GET /api/acesso/eu': json(200, eu()) })
    abrir('/documentos/arquivados')
    expect(await screen.findByText(/só da Comissão e da administração/)).toBeTruthy()
  })
})

// --- documento aberto (H-18, H-19) -------------------------------------------------------------

describe('documento aberto', () => {
  const comVersoes = documento(1, {
    titulo: 'Cronograma da obra',
    versao: 2,
    atualizado_em: '2026-10-20T12:00:00Z',
    versoes_anteriores: [
      {
        versao: 1,
        enviada_em: '2026-10-02T12:00:00Z',
        arquivo: { id: 5, nome: 'cronograma-antigo.pdf', tipo: 'application/pdf', tamanho_bytes: 1000 },
      },
    ],
  })

  it('mostra o documento, abre numa aba e baixa na própria tela', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
      'GET /api/documentos/1/versoes/2/link': json(200, LINK),
      'GET /api/documentos/1/versoes/2/link?baixar=true': json(200, LINK),
    })
    const aba = abaFalsa()
    const irPara = vi.spyOn(navegador, 'irPara').mockImplementation(() => {})
    abrir('/documentos/1')
    expect(await screen.findByRole('heading', { level: 1, name: 'Cronograma da obra' })).toBeTruthy()
    expect(screen.getByText(/PDF, 2,4 MB/)).toBeTruthy()
    expect(screen.getByText(/Versão 2/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Abrir o documento/ }))
    await waitFor(() => expect(aba.location.href).toBe(LINK.url))
    expect(aba.opener).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /Baixar/ }))
    await waitFor(() => expect(irPara).toHaveBeenCalledWith(LINK.url))
    expect(chamadas.map((c) => c.caminho)).toContain('/api/documentos/1/versoes/2/link?baixar=true')
    expect(screen.queryByRole('link', { name: /Enviar nova versão/ })).toBeNull()
  })

  it('as versões anteriores, com data, abrem o arquivo daquela versão', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
      'GET /api/documentos/1/versoes/1/link': json(200, LINK),
    })
    const aba = abaFalsa()
    abrir('/documentos/1')
    const secao = await screen.findByRole('region', { name: 'Versões anteriores' })
    expect(secao.textContent).toContain('Versão 1')
    expect(secao.textContent).toContain('2 de outubro')
    fireEvent.click(within(secao).getByRole('button', { name: /Abrir a versão 1/ }))
    await waitFor(() => expect(aba.location.href).toBe(LINK.url))
  })

  it('sem a aba (bloqueada), vai para o arquivo na própria tela', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
      'GET /api/documentos/1/versoes/2/link': json(200, LINK),
    })
    vi.spyOn(navegador, 'abrirAba').mockReturnValue(null)
    const irPara = vi.spyOn(navegador, 'irPara').mockImplementation(() => {})
    abrir('/documentos/1')
    fireEvent.click(await screen.findByRole('button', { name: /Abrir o documento/ }))
    await waitFor(() => expect(irPara).toHaveBeenCalledWith(LINK.url))
  })

  it('erro ao pedir o link: fecha a aba e mostra a mensagem', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
      'GET /api/documentos/1/versoes/2/link': json(503, {
        codigo: 'arquivos_desligados',
        mensagem: 'O envio de arquivos ainda não está ligado no Portal.',
      }),
    })
    const aba = abaFalsa()
    abrir('/documentos/1')
    fireEvent.click(await screen.findByRole('button', { name: /Abrir o documento/ }))
    expect(await screen.findByText('O envio de arquivos ainda não está ligado no Portal.')).toBeTruthy()
    expect(aba.close).toHaveBeenCalled()
  })

  it('documento que não existe (ou que a unidade não vê)', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/9': json(404, {
        codigo: 'documento_nao_encontrado',
        mensagem: 'Não achamos este documento.',
      }),
    })
    abrir('/documentos/9')
    expect(await screen.findByText(/Não achamos este documento/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ir para os documentos' })).toBeTruthy()
  })

  it('para a gestão: nova versão e arquivar com confirmação', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['comissao'])),
      'GET /api/documentos/1': json(200, comVersoes),
      'POST /api/documentos/1/arquivar': json(200, {
        ...comVersoes,
        arquivado_em: '2026-10-21T12:00:00Z',
      }),
    })
    abrir('/documentos/1')
    const nova = await screen.findByRole('link', { name: /Enviar nova versão/ })
    expect(nova.getAttribute('href')).toBe('/documentos/1/nova-versao')
    fireEvent.click(screen.getByRole('button', { name: 'Arquivar' }))
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: /Arquivar de vez/ }))
    expect(await screen.findByText(/Arquivado em 21 de outubro/)).toBeTruthy()
    expect(screen.queryByRole('link', { name: /Enviar nova versão/ })).toBeNull()
  })
})

// --- públicos (H-18) ---------------------------------------------------------------------------

describe('documentos públicos', () => {
  it('sem entrar: a lista dos públicos, cada um abre e baixa', async () => {
    apiFalsa({
      'GET /api/documentos/publicos': json(200, {
        itens: [resumo(1, { titulo: 'Como acessar o Portal', categoria: 'orientacao', acesso: 'publico' })],
      }),
      'GET /api/documentos/1/versoes/1/link': json(200, LINK),
    })
    const aba = abaFalsa()
    abrir('/documentos/publicos')
    expect(await screen.findByRole('heading', { name: 'Orientações' })).toBeTruthy()
    expect(screen.getByText(/aparecem depois que você entra/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Abrir Como acessar o Portal/ }))
    await waitFor(() => expect(aba.location.href).toBe(LINK.url))
    expect(screen.getByRole('button', { name: /Baixar Como acessar o Portal/ })).toBeTruthy()
  })

  it('sem nenhum público', async () => {
    apiFalsa({ 'GET /api/documentos/publicos': json(200, { itens: [] }) })
    abrir('/documentos/publicos')
    expect(await screen.findByText('Nenhum documento público ainda.')).toBeTruthy()
  })
})

// --- publicar (H-17) ---------------------------------------------------------------------------

const ENVIO = {
  arquivo_id: 42,
  url: 'https://r2.falso/envios/abc',
  content_type: 'application/pdf',
  expira_em: '2026-10-12T12:10:00Z',
}
const ENVIADO = { id: 42, nome: 'regimento.pdf', tipo: 'application/pdf', tamanho_bytes: 9 }

function escolherArquivo(nome = 'regimento.pdf', conteudo = '%PDF-1.7') {
  const arquivo = new File([conteudo], nome, { type: 'application/pdf' })
  fireEvent.change(screen.getByLabelText(/Escolher PDF ou foto/), { target: { files: [arquivo] } })
  return arquivo
}

/** A `apiFalsa` da casca lê todo corpo como JSON; o PUT do envio leva o arquivo. Aqui o corpo
 *  que não é JSON vira `undefined` antes de chegar nela. */
function apiDoEnvio(extra: Record<string, Response | ((corpo: unknown) => Response)> = {}) {
  const chamadas = apiFalsaBase(extra)
  const falsa = globalThis.fetch as unknown as (c: string, o?: RequestInit) => Promise<Response>
  vi.stubGlobal(
    'fetch',
    vi.fn((caminho: string, opcoes?: RequestInit) =>
      falsa(caminho, typeof opcoes?.body === 'string' ? opcoes : { ...opcoes, body: undefined }),
    ),
  )
  return chamadas
}

function apiFalsaBase(extra: Record<string, Response | ((corpo: unknown) => Response)>) {
  return apiFalsa({
    'GET /api/acesso/eu': json(200, eu(['comissao'])),
    'POST /api/arquivos': json(201, ENVIO),
    'PUT https://r2.falso/envios/abc': new Response(null, { status: 200 }),
    'POST /api/arquivos/42/confirmar': json(200, ENVIADO),
    'GET /api/documentos/5': json(200, documento(5, { titulo: 'Regimento interno' })),
    ...extra,
  })
}

describe('novo documento', () => {
  it('envia o arquivo, publica e abre o documento publicado', async () => {
    const chamadas = apiDoEnvio({
      'POST /api/documentos': json(201, documento(5, { titulo: 'Regimento interno' })),
    })
    const roteador = abrir('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), {
      target: { value: 'Regimento interno' },
    })
    fireEvent.change(screen.getByLabelText('Assunto'), { target: { value: 'regimento' } })
    fireEvent.change(screen.getByLabelText('Data do documento'), {
      target: { value: '2026-10-05' },
    })
    escolherArquivo()
    expect(screen.getByText(/regimento\.pdf/)).toBeTruthy()
    const avisar = screen.getByRole('checkbox', { name: /Avisar os apartamentos/ }) as HTMLInputElement
    expect(avisar.checked).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    const publicar = chamadas.find((c) => c.metodo === 'POST' && c.caminho === '/api/documentos')
    expect(publicar?.corpo).toEqual({
      titulo: 'Regimento interno',
      categoria: 'regimento',
      data_documento: '2026-10-05',
      acesso: 'compradores',
      arquivo_id: 42,
      avisar_unidades: true,
    })
    expect(chamadas.find((c) => c.caminho === '/api/arquivos')?.corpo).toMatchObject({
      finalidade: 'documento',
    })
  })

  it('"Só a gestão" tira a opção de avisar', async () => {
    const chamadas = apiDoEnvio({
      'POST /api/documentos': json(201, documento(5)),
    })
    abrir('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Ata' } })
    fireEvent.click(screen.getByRole('radio', { name: /Só a gestão/ }))
    expect(screen.queryByRole('checkbox', { name: /Avisar/ })).toBeNull()
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/documentos')?.corpo).toMatchObject({
        acesso: 'gestao',
        avisar_unidades: false,
      }),
    )
  })

  it('sem título ou sem arquivo: diz o que falta e não envia nada', async () => {
    const chamadas = apiDoEnvio()
    abrir('/documentos/novo')
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar documento' }))
    expect(await screen.findAllByText('Escreva o título do documento.')).not.toHaveLength(0)
    expect(screen.getAllByText('Escolha o arquivo do documento.')).not.toHaveLength(0)
    expect(chamadas.filter((c) => c.metodo !== 'GET')).toEqual([])
  })

  it('a publicação falhou: a próxima tentativa usa o arquivo já enviado', async () => {
    let vez = 0
    const chamadas = apiDoEnvio({
      'POST /api/documentos': () =>
        ++vez === 1
          ? json(422, {
              codigo: 'dados_invalidos',
              mensagem: 'Confira os campos marcados.',
              campos: [{ campo: 'titulo', mensagem: 'O título pode ter até 120 letras.' }],
            })
          : json(201, documento(5)),
    })
    const roteador = abrir('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Regimento' } })
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    expect(await screen.findByText('O título pode ter até 120 letras.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(chamadas.filter((c) => c.caminho === '/api/arquivos')).toHaveLength(1)
  })

  it('arquivo recusado: a mensagem aparece junto do arquivo', async () => {
    apiDoEnvio({
      'POST /api/arquivos/42/confirmar': json(422, {
        codigo: 'arquivo_recusado',
        mensagem: 'Este arquivo não é um PDF nem uma foto (JPEG, PNG ou WEBP). Escolha outro.',
      }),
    })
    abrir('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Regimento' } })
    escolherArquivo('programa.pdf', 'MZ')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    const erros = await screen.findAllByText(/não é um PDF nem uma foto/)
    expect(erros.length).toBeGreaterThan(0)
  })
})

describe('nova versão', () => {
  it('envia o arquivo e volta ao documento', async () => {
    const chamadas = apiDoEnvio({
      'GET /api/documentos/5': json(200, documento(5, { titulo: 'Regimento interno' })),
      'POST /api/documentos/5/versoes': json(201, documento(5, { versao: 2 })),
    })
    const roteador = abrir('/documentos/5/nova-versao')
    expect(await screen.findByText(/Regimento interno/)).toBeTruthy()
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar nova versão' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(chamadas.find((c) => c.caminho === '/api/documentos/5/versoes')?.corpo).toEqual({
      arquivo_id: 42,
    })
  })

  it('sem arquivo não envia', async () => {
    const chamadas = apiDoEnvio()
    abrir('/documentos/5/nova-versao')
    fireEvent.click(await screen.findByRole('button', { name: 'Enviar nova versão' }))
    expect(await screen.findAllByText('Escolha o arquivo da versão nova.')).not.toHaveLength(0)
    expect(chamadas.filter((c) => c.metodo !== 'GET')).toEqual([])
  })
})
