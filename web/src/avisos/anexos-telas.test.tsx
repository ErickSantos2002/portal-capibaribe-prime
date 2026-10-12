// M3 · Épico B: anexos nas telas de avisos, com uma API de mentira (spec `m3-anexos.md`, 3).
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroDaApi } from '../api/cliente'
import type { Eu, Papel } from '../api/tipos'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { rotas } from '../rotas'
import type { AvisoCompleto, AvisoResumo } from './tipos'

const enviarArquivo = vi.hoisted(() => vi.fn())
vi.mock('../arquivos/enviar', () => ({ enviarArquivo }))

function eu(papeis: Papel[] = []): Eu {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    papeis,
    gestao: papeis.length > 0,
    admin: papeis.includes('admin'),
    precisa_trocar_senha: false,
  }
}

const FOTO: ArquivoEnviado = { id: 11, nome: 'fundação.webp', tipo: 'image/webp', tamanho_bytes: 1.24 * 1024 * 1024 }
const PDF: ArquivoEnviado = { id: 12, nome: 'Regras da visita.pdf', tipo: 'application/pdf', tamanho_bytes: 320 * 1024 }

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
    categoria: 'obra',
    evento_quando: null,
    quantidade_anexos: 0,
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
    anexos: [],
    documento: null,
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

function api(sessao: Eu, rota: Rota) {
  const fetch = vi.fn(async (caminho: string, init: RequestInit = {}) => {
    const url = new URL(caminho, 'https://portal.test')
    if (url.pathname === '/api/acesso/eu') return json(200, sessao)
    if (url.pathname === '/api/avisos/nao-lidos') return json(200, { quantidade: 0 })
    if (url.pathname === '/api/avisos/destinos') {
      return json(200, { blocos: [{ numero: 1, nome: 'Bloco 1' }] })
    }
    if (url.pathname === '/api/avisos/alcance') return json(200, { unidades: 320 })
    if (url.pathname.endsWith('/lido')) return json(204, null)
    return (
      rota(url, init) ?? json(404, { codigo: 'aviso_nao_encontrado', mensagem: 'Não achamos.' })
    )
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** O link de 5 minutos de um anexo, como a API falsa devolve. */
function link(url: URL): Response | undefined {
  const achado = url.pathname.match(/^\/api\/avisos\/(\d+)\/anexos\/(\d+)\/link$/)
  if (!achado) return undefined
  return json(200, {
    url: `https://r2.test/arquivos/${achado[2]}?baixar=${url.searchParams.get('baixar') ?? ''}`,
    expira_em: '2026-11-03T12:05:00Z',
  })
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: [caminho] })
  render(<RouterProvider router={roteador} />)
  return roteador
}

beforeEach(() => {
  enviarArquivo.mockReset()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('aviso aberto com anexos', () => {
  it('a foto aparece pelo link e abre grande; o foco volta ao fechar', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO, PDF] })) : link(url),
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', {
      name: 'Ver a foto fundação.webp em tamanho grande',
    })
    const miniatura = await within(botao).findByRole('img')
    await waitFor(() => expect(miniatura.getAttribute('src')).toBe('https://r2.test/arquivos/11?baixar='))
    expect(miniatura.getAttribute('alt')).toBe('Foto: fundação.webp')

    fireEvent.click(botao)
    const janela = screen.getByRole('dialog', { name: 'Foto: fundação.webp' })
    const fechar = within(janela).getByRole('button', { name: 'Fechar' })
    expect(document.activeElement).toBe(fechar)
    fireEvent.keyDown(janela, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(botao)
  })

  it('a foto que falha pede o link de novo uma vez, depois oferece tentar de novo', async () => {
    const fetch = api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO] })) : link(url),
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', { name: /Ver a foto/ })
    const imagem = await within(botao).findByRole('img')
    await waitFor(() => expect(imagem.getAttribute('src')).toBeTruthy())
    fireEvent.error(imagem)
    await waitFor(() =>
      expect(fetch.mock.calls.filter(([c]) => String(c).includes('/anexos/11/link'))).toHaveLength(2),
    )
    fireEvent.error(await within(botao).findByRole('img'))
    expect(await screen.findByText('Não deu para mostrar a foto.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    await waitFor(() =>
      expect(fetch.mock.calls.filter(([c]) => String(c).includes('/anexos/11/link'))).toHaveLength(3),
    )
  })

  it('o PDF é um botão com nome e tamanho que abre o link numa aba nova', async () => {
    const aba = { opener: {}, location: { href: '' }, close: vi.fn() }
    const open = vi.fn(() => aba)
    vi.stubGlobal('open', open)
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [PDF] })) : link(url),
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', { name: /Regras da visita\.pdf/ })
    expect(botao.textContent).toContain('PDF, 320 KB')
    fireEvent.click(botao)
    expect(open).toHaveBeenCalledWith('', '_blank')
    await waitFor(() => expect(aba.location.href).toBe('https://r2.test/arquivos/12?baixar='))
    expect(aba.opener).toBeNull()
  })

  it('o link do PDF falhou: fecha a aba e mostra a mensagem', async () => {
    const aba = { opener: {}, location: { href: '' }, close: vi.fn() }
    vi.stubGlobal('open', vi.fn(() => aba))
    api(eu(), (url) => {
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { anexos: [PDF] }))
      return json(503, {
        codigo: 'arquivos_desligados',
        mensagem: 'O envio de arquivos ainda não está ligado no Portal.',
      })
    })
    abrir('/avisos/5')
    fireEvent.click(await screen.findByRole('button', { name: /Regras da visita\.pdf/ }))
    expect(
      await screen.findByText('O envio de arquivos ainda não está ligado no Portal.'),
    ).toBeTruthy()
    expect(aba.close).toHaveBeenCalled()
  })

  it('a versão antiga mostra os anexos dela', async () => {
    const aviso = completo(5, {
      editado_em: '2026-11-04T12:00:00Z',
      anexos: [],
      versoes_anteriores: [
        {
          versao: 1,
          titulo: 'Antes',
          texto: 'Com o PDF',
          criada_em: '2026-11-03T12:00:00Z',
          categoria: 'obra',
          evento: null,
          anexos: [PDF],
        },
      ],
    })
    api(eu(), (url) => (url.pathname === '/api/avisos/5' ? json(200, aviso) : link(url)))
    abrir('/avisos/5')
    const antes = (await screen.findByText('Antes')).closest('section')!
    expect(within(antes).getByRole('button', { name: /Regras da visita\.pdf/ })).toBeTruthy()
  })

  it('sem anexo, nada aparece', async () => {
    api(eu(), (url) => (url.pathname === '/api/avisos/5' ? json(200, completo(5)) : undefined))
    abrir('/avisos/5')
    await screen.findByText('Texto 5')
    expect(screen.queryByRole('region', { name: 'Anexos' })).toBeNull()
  })
})

describe('mural', () => {
  it('o clipe com quantos anexos, no cartão e no fixado', async () => {
    const itens = [
      resumo(1, { titulo: 'Fixado', fixado: true, quantidade_anexos: 1 }),
      resumo(2, { titulo: 'Com três', quantidade_anexos: 3 }),
      resumo(3, { titulo: 'Sem anexo' }),
    ]
    api(eu(), (url) => (url.pathname === '/api/avisos' ? json(200, { itens }) : undefined))
    abrir('/avisos')
    const fixado = (await screen.findByText('Fixado')).closest('a')!
    expect(within(fixado).getByText('1 anexo')).toBeTruthy()
    const tres = screen.getByText('Com três').closest('a')!
    expect(within(tres).getByText('3 anexos')).toBeTruthy()
    const sem = screen.getByText('Sem anexo').closest('a')!
    expect(sem.querySelector('.com-anexo')).toBeNull()
  })
})

/** Um `File` de mentira (o jsdom não tem o conteúdo de verdade, nem precisa). */
function arquivo(nome: string, tipo: string) {
  return new File(['x'], nome, { type: tipo })
}

function escolher(...arquivos: File[]) {
  const campo = screen.getByLabelText('Anexar foto ou PDF') as HTMLInputElement
  fireEvent.change(campo, { target: { files: arquivos } })
}

async function preencher() {
  fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Visita' } })
  fireEvent.change(screen.getByLabelText('Texto do aviso'), { target: { value: 'Regras no PDF.' } })
}

describe('formulário: novo aviso com anexos', () => {
  it('envia cada arquivo, mostra pronto e manda os ids ao publicar', async () => {
    const fetch = api(eu(['comissao']), (url, init) =>
      url.pathname === '/api/avisos' && init.method === 'POST'
        ? json(201, completo(9, { anexos: [PDF] }))
        : url.pathname === '/api/avisos'
          ? json(200, { itens: [] })
          : undefined,
    )
    enviarArquivo.mockResolvedValueOnce(PDF)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('Regras da visita.pdf', 'application/pdf'))
    expect(screen.getByText('Enviando…')).toBeTruthy()
    expect(await screen.findByText('PDF, 320 KB')).toBeTruthy()
    expect(enviarArquivo).toHaveBeenCalledWith(expect.any(File), 'aviso')

    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    const previa = await screen.findByText('E assim, quando alguém abrir')
    expect(previa).toBeTruthy()
    expect(screen.getAllByText(/Regras da visita\.pdf/).length).toBeGreaterThan(1)
    fireEvent.click(screen.getByRole('button', { name: 'Publicar aviso' }))
    await waitFor(() =>
      expect(fetch.mock.calls.some(([c, i]) => String(c) === '/api/avisos' && i?.method === 'POST')).toBe(true),
    )
    const [, init] = fetch.mock.calls.find(([c, i]) => String(c) === '/api/avisos' && i?.method === 'POST')!
    expect(JSON.parse(String(init!.body)).anexos).toEqual([12])
  })

  it('um de cada vez, na ordem; tirar some da lista', async () => {
    let terminar: (a: ArquivoEnviado) => void = () => {}
    enviarArquivo.mockImplementationOnce(() => new Promise((r) => (terminar = r)))
    enviarArquivo.mockResolvedValueOnce(FOTO)
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('a.pdf', 'application/pdf'), arquivo('fundação.jpg', 'image/jpeg'))
    await waitFor(() => expect(enviarArquivo).toHaveBeenCalledTimes(1))
    expect(screen.getByText('Enviando 1 de 2…')).toBeTruthy()
    // O segundo espera o primeiro terminar.
    await act(async () => {})
    expect(enviarArquivo).toHaveBeenCalledTimes(1)
    await act(async () => terminar(PDF))
    await waitFor(() => expect(enviarArquivo).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Foto, 1,2 MB')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Tirar Regras da visita.pdf' }))
    expect(screen.queryByText('PDF, 320 KB')).toBeNull()
  })

  it('erro no envio: mensagem, tentar de novo, e não publica enquanto isso', async () => {
    enviarArquivo.mockRejectedValueOnce(
      new ErroDaApi(409, {
        codigo: 'arquivo_nao_chegou',
        mensagem: 'O arquivo não chegou ao Portal. Confira a internet e envie de novo.',
      }),
    )
    enviarArquivo.mockResolvedValueOnce(PDF)
    const fetch = api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('Regras da visita.pdf', 'application/pdf'))
    expect(
      await screen.findByText('O arquivo não chegou ao Portal. Confira a internet e envie de novo.'),
    ).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Ver prévia' }))
    expect(
      (await screen.findAllByText('Tire ou envie de novo o arquivo que deu erro.')).length,
    ).toBeGreaterThan(0)
    expect(screen.queryByText('E assim, quando alguém abrir')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar de novo Regras da visita.pdf' }))
    expect(await screen.findByText('PDF, 320 KB')).toBeTruthy()
    expect(fetch.mock.calls.some(([, i]) => i?.method === 'POST')).toBe(false)
  })

  it('arquivo recusado pelo conteúdo: só "Tirar" (enviar de novo daria o mesmo erro)', async () => {
    enviarArquivo.mockRejectedValueOnce(
      new ErroDaApi(422, {
        codigo: 'arquivo_recusado',
        mensagem: 'Este arquivo não é um PDF nem uma foto (JPEG, PNG ou WEBP). Escolha outro.',
      }),
    )
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('mapa.pdf', 'application/pdf'))
    expect(await screen.findByText(/não é um PDF nem uma foto/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Enviar de novo mapa.pdf' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Tirar mapa.pdf' })).toBeTruthy()
  })

  it('até 5: os que sobram ficam de fora com aviso, e o botão some', async () => {
    enviarArquivo.mockImplementation(async (f: File) => ({ ...PDF, nome: f.name }))
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(
      ...['1', '2', '3', '4', '5', '6', '7'].map((n) => arquivo(`${n}.pdf`, 'application/pdf')),
    )
    expect(
      screen.getByText('Até 5 anexos por aviso. Ficaram de fora: 6.pdf, 7.pdf.'),
    ).toBeTruthy()
    await waitFor(() => expect(enviarArquivo).toHaveBeenCalledTimes(5))
    expect(screen.queryByLabelText('Anexar foto ou PDF')).toBeNull()
    expect(screen.getByText('Já são 5 anexos, o máximo.')).toBeTruthy()
  })
})

describe('formulário: corrigir aviso com anexos', () => {
  it('começa com os anexos em vigor e manda a lista explícita', async () => {
    const fetch = api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') {
        return json(200, completo(5, { anexos: [PDF] }))
      }
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { anexos: [FOTO, PDF] }))
      return link(url)
    })
    abrir('/avisos/5/corrigir')
    expect(await screen.findByText('Foto, 1,2 MB')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Tirar fundação.webp' }))
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() =>
      expect(fetch.mock.calls.some(([, i]) => i?.method === 'PUT')).toBe(true),
    )
    const [, init] = fetch.mock.calls.find(([, i]) => i?.method === 'PUT')!
    expect(JSON.parse(String(init!.body)).anexos).toEqual([12])
  })

  it('o erro da API no campo anexos aparece embaixo do campo', async () => {
    api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') {
        return json(422, {
          codigo: 'dados_invalidos',
          mensagem: 'Envie o arquivo de novo.',
          campos: [{ campo: 'anexos', mensagem: 'Envie o arquivo de novo.' }],
        })
      }
      if (url.pathname === '/api/avisos/5') return json(200, completo(5, { anexos: [PDF] }))
      return link(url)
    })
    abrir('/avisos/5/corrigir')
    await screen.findByText('PDF, 320 KB')
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    const mensagens = await screen.findAllByText('Envie o arquivo de novo.')
    expect(mensagens.some((m) => m.classList.contains('avisos-erro-campo'))).toBe(true)
  })
})
