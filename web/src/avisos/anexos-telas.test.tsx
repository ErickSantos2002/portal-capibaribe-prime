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

const FOTO2: ArquivoEnviado = { id: 13, nome: 'IMG_2031.webp', tipo: 'image/webp', tamanho_bytes: 900 * 1024 }

describe('aviso aberto com anexos', () => {
  it('fotos pela rota de abrir do Portal, sem o nome técnico; tocar abre grande', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO, FOTO2, PDF] })) : undefined,
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', { name: 'Ver a foto 1 de 2 em tamanho grande' })
    const miniatura = within(botao).getByRole('img')
    expect(miniatura.getAttribute('src')).toBe('/api/avisos/5/anexos/11/abrir')
    expect(miniatura.getAttribute('alt')).toBe('Foto 1 de 2')
    // U9: a miniatura diz que amplia.
    expect(botao.textContent).toContain('Ampliar')
    // U7: o nome do arquivo da foto não aparece para o morador.
    expect(document.body.textContent).not.toContain('IMG_2031')

    fireEvent.click(botao)
    const janela = screen.getByRole('dialog', { name: 'Foto 1 de 2' })
    expect(within(janela).getByRole('img').getAttribute('src')).toBe('/api/avisos/5/anexos/11/abrir')
    expect(document.activeElement).toBe(within(janela).getByRole('button', { name: 'Fechar' }))
  })

  it('visualizador: próxima e anterior, setas do teclado, Esc e o foco volta à foto vista', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO, FOTO2] })) : undefined,
    )
    abrir('/avisos/5')
    fireEvent.click(await screen.findByRole('button', { name: 'Ver a foto 1 de 2 em tamanho grande' }))
    fireEvent.click(screen.getByRole('button', { name: 'Próxima foto' }))
    const janela = screen.getByRole('dialog', { name: 'Foto 2 de 2' })
    expect(within(janela).getByRole('img').getAttribute('src')).toBe('/api/avisos/5/anexos/13/abrir')
    fireEvent.keyDown(document, { key: 'ArrowLeft' })
    expect(screen.getByRole('dialog', { name: 'Foto 1 de 2' })).toBeTruthy()
    fireEvent.keyDown(document, { key: 'ArrowRight' })
    // C4: clicar na foto (fora dos botões) não tira o foco do diálogo e o Esc continua valendo.
    fireEvent.mouseDown(within(screen.getByRole('dialog')).getByRole('img'))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Ver a foto 2 de 2 em tamanho grande' }),
    )
  })

  it('C4: com o visualizador aberto, a página de trás fica inerte e o foco não sai', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO] })) : undefined,
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', { name: 'Ver a foto 1 de 1 em tamanho grande' })
    fireEvent.click(botao)
    const janela = screen.getByRole('dialog')
    const fundo = [...document.body.children].filter((e) => !e.contains(janela))
    expect(fundo.length).toBeGreaterThan(0)
    expect(fundo.every((e) => e.hasAttribute('inert'))).toBe(true)
    // Só uma foto: sem "Anterior"/"Próxima".
    expect(within(janela).queryByRole('button', { name: 'Próxima foto' })).toBeNull()
    act(() => botao.focus())
    expect(janela.contains(document.activeElement)).toBe(true)
    fireEvent.click(within(janela).getByRole('button', { name: 'Fechar' }))
    expect(fundo.some((e) => e.hasAttribute('inert'))).toBe(false)
  })

  it('a foto que falha é pedida de novo uma vez, depois oferece tentar de novo', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [FOTO] })) : undefined,
    )
    abrir('/avisos/5')
    const botao = await screen.findByRole('button', { name: /Ver a foto/ })
    fireEvent.error(within(botao).getByRole('img'))
    expect(within(botao).getByRole('img').getAttribute('src')).toBe(
      '/api/avisos/5/anexos/11/abrir?tentativa=2',
    )
    fireEvent.error(within(botao).getByRole('img'))
    expect(await screen.findByText('Não deu para mostrar a foto.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar de novo' }))
    const outra = await screen.findByRole('button', { name: /Ver a foto/ })
    expect(within(outra).getByRole('img').getAttribute('src')).toBe(
      '/api/avisos/5/anexos/11/abrir?tentativa=3',
    )
  })

  it('U12: o PDF é um link do Portal que abre em outra aba (link novo a cada toque)', async () => {
    api(eu(), (url) =>
      url.pathname === '/api/avisos/5' ? json(200, completo(5, { anexos: [PDF] })) : undefined,
    )
    abrir('/avisos/5')
    const link = await screen.findByRole('link', { name: /Regras da visita\.pdf/ })
    expect(link.textContent).toContain('PDF, 320 KB')
    expect(link.getAttribute('href')).toBe('/api/avisos/5/anexos/12/abrir')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
  })

  it('a versão antiga mostra os anexos dela, e a correção diz o que mudou nos anexos', async () => {
    const COMUNICADO = { ...PDF, id: 14, nome: 'Comunicado.pdf' }
    const aviso = completo(5, {
      editado_em: '2026-11-04T12:00:00Z',
      anexos: [PDF, COMUNICADO],
      versoes_anteriores: [
        {
          versao: 1,
          titulo: 'Antes',
          texto: 'Com o PDF',
          criada_em: '2026-11-03T12:00:00Z',
          categoria: 'obra',
          evento: null,
          anexos: [FOTO, PDF],
        },
      ],
    })
    api(eu(), (url) => (url.pathname === '/api/avisos/5' ? json(200, aviso) : undefined))
    abrir('/avisos/5')
    const antes = (await screen.findByText('Antes')).closest('section')!
    expect(within(antes).getByRole('link', { name: /Regras da visita\.pdf/ })).toBeTruthy()
    expect(within(antes).getByText(/Assim era antes/)).toBeTruthy()
    // U6
    expect(screen.getByText('Anexos: entrou Comunicado.pdf; saiu 1 foto.')).toBeTruthy()
    expect(screen.getByText('Como está agora:')).toBeTruthy()
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
    expect((await screen.findAllByText(/não é um PDF nem uma foto/)).length).toBeGreaterThan(0)
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

describe('formulário: revisão de UX e de código', () => {
  it('U3: durante o envio, o botão espera os arquivos (desabilitado); U2: nada fica para trás', async () => {
    let terminar: (a: ArquivoEnviado) => void = () => {}
    enviarArquivo.mockImplementationOnce(() => new Promise((r) => (terminar = r)))
    enviarArquivo.mockResolvedValueOnce(FOTO)
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('a.pdf', 'application/pdf'), arquivo('b.jpg', 'image/jpeg'))
    const botao = await screen.findByRole('button', { name: 'Esperando os arquivos… (0 de 2)' })
    expect((botao as HTMLButtonElement).disabled).toBe(true)
    await act(async () => terminar(PDF))
    expect(await screen.findByRole('button', { name: 'Ver prévia' })).toBeTruthy()
    expect(screen.queryByText('Espere os arquivos terminarem de enviar.')).toBeNull()
  })

  it('U4: anuncia cada arquivo pronto ou recusado, com o motivo', async () => {
    enviarArquivo.mockResolvedValueOnce(PDF)
    enviarArquivo.mockRejectedValueOnce(
      new ErroDaApi(422, { codigo: 'arquivo_recusado', mensagem: 'O arquivo pode ter até 10 MB.' }),
    )
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('Regras da visita.pdf', 'application/pdf'), arquivo('grande.jpg', 'image/jpeg'))
    const regiao = document.querySelector('.anexos-anuncio')!
    expect(regiao.getAttribute('aria-live')).toBe('polite')
    await waitFor(() =>
      expect(regiao.textContent).toBe('Não deu para anexar grande.jpg: O arquivo pode ter até 10 MB.'),
    )
  })

  it('U5: depois de "Tirar", o foco vai para o próximo item ou para "Anexar foto ou PDF"', async () => {
    let id = 100
    enviarArquivo.mockImplementation(async (f: File) => ({ ...PDF, id: id++, nome: f.name }))
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    escolher(arquivo('um.pdf', 'application/pdf'), arquivo('dois.pdf', 'application/pdf'))
    await waitFor(() => expect(screen.getAllByText(/^PDF, /)).toHaveLength(2))
    fireEvent.click(screen.getByRole('button', { name: 'Tirar um.pdf' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Tirar dois.pdf' })),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tirar dois.pdf' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByLabelText('Anexar foto ou PDF')),
    )
  })

  it('U10 e U11: a ajuda diz quando o envio começa; com 5 e erro, a frase manda tirar', async () => {
    enviarArquivo.mockRejectedValue(
      new ErroDaApi(422, { codigo: 'arquivo_recusado', mensagem: 'O arquivo pode ter até 10 MB.' }),
    )
    api(eu(['comissao']), () => undefined)
    abrir('/avisos/novo')
    await preencher()
    expect(screen.getByText(/O envio começa assim que você escolhe/)).toBeTruthy()
    escolher(...['1', '2', '3', '4', '5'].map((n) => arquivo(`${n}.jpg`, 'image/jpeg')))
    expect(
      await screen.findByText('Já são 5 arquivos. Tire os que deram erro para anexar outros.'),
    ).toBeTruthy()
  })

  it('U1: sair com algo escrito pede confirmação; "Continuar escrevendo" fica', async () => {
    api(eu(['comissao']), (url) =>
      url.pathname === '/api/avisos' ? json(200, { itens: [] }) : undefined,
    )
    const roteador = abrir('/avisos/novo')
    await preencher()
    await act(async () => {
      await roteador.navigate('/avisos')
    })
    const pergunta = screen.getByRole('alertdialog', { name: 'Sair sem publicar?' })
    expect(pergunta.textContent).toContain('O que você escreveu e os anexos vão se perder.')
    fireEvent.click(within(pergunta).getByRole('button', { name: 'Continuar escrevendo' }))
    expect(roteador.state.location.pathname).toBe('/avisos/novo')
    await act(async () => {
      await roteador.navigate('/avisos')
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sair sem publicar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
  })

  it('U1: formulário vazio sai sem perguntar; recarregar com texto pede confirmação', async () => {
    api(eu(['comissao']), (url) =>
      url.pathname === '/api/avisos' ? json(200, { itens: [] }) : undefined,
    )
    const roteador = abrir('/avisos/novo')
    await screen.findByLabelText('Título')
    const vazio = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(vazio)
    expect(vazio.defaultPrevented).toBe(false)
    await preencher()
    const comTexto = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(comTexto)
    expect(comTexto.defaultPrevented).toBe(true)
    fireEvent.change(screen.getByLabelText('Título'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Texto do aviso'), { target: { value: '' } })
    await act(async () => {
      await roteador.navigate('/avisos')
    })
    expect(screen.queryByRole('alertdialog')).toBeNull()
    expect(roteador.state.location.pathname).toBe('/avisos')
  })

  it('C2: a correção manda a versão de origem; se outra pessoa corrigiu, avisa e recarrega', async () => {
    let vezes = 0
    const V1 = {
      versao: 1,
      titulo: 'V1',
      texto: 'x',
      criada_em: '2026-11-03T12:00:00Z',
      categoria: 'obra' as const,
      evento: null,
      anexos: [],
    }
    const fetch = api(eu(['comissao']), (url, init) => {
      if (url.pathname === '/api/avisos/5' && init.method === 'PUT') {
        return json(409, {
          codigo: 'aviso_corrigido_agora',
          mensagem: 'Outra pessoa corrigiu este aviso agora há pouco. Abra de novo e confira.',
        })
      }
      if (url.pathname === '/api/avisos/5') {
        vezes += 1
        return json(
          200,
          vezes > 1
            ? completo(5, { texto: 'Versão nova', anexos: [PDF], versoes_anteriores: [V1] })
            : completo(5, { anexos: [PDF] }),
        )
      }
      return undefined
    })
    abrir('/avisos/5/corrigir')
    fireEvent.change(await screen.findByLabelText('Texto do aviso'), {
      target: { value: 'Meu texto' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar correção' }))
    await waitFor(() => expect(fetch.mock.calls.some(([, i]) => i?.method === 'PUT')).toBe(true))
    const [, init] = fetch.mock.calls.find(([, i]) => i?.method === 'PUT')!
    expect(JSON.parse(String(init!.body)).versao_base).toBe(1)
    expect(await screen.findByText(/Outra pessoa corrigiu este aviso agora há pouco/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Abrir a versão nova' }))
    await waitFor(() =>
      expect((screen.getByLabelText('Texto do aviso') as HTMLTextAreaElement).value).toBe(
        'Versão nova',
      ),
    )
  })
})
