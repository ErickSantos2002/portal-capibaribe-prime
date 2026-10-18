// Épico A do M3 · telas dos documentos com uma API de mentira: cada critério de H-17, H-18 e
// H-19 que aparece na tela, e os achados da revisão de UX (U1 a U17).
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import { DocumentoDoAviso } from './DocumentoDoAviso'
import { itemDocumentos } from './menu'
import type { Documento, DocumentoResumo } from './tipos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const MB = 1024 * 1024

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

// --- menu e encaixes ---------------------------------------------------------------------------

describe('encaixes', () => {
  it('o menu tem "Documentos" para toda unidade', () => {
    for (const quem of [eu(), eu(['comissao'])]) {
      expect(itemDocumentos(quem)).toMatchObject({
        para: '/documentos',
        icone: 'documentos',
        texto: 'Documentos',
        curto: 'Docs',
        grupo: 'dia-a-dia',
        naBarra: 3,
      })
    }
  })

  it('U8: o aviso automático leva à página do documento, "Ver o documento"', () => {
    render(
      createElement(
        MemoryRouter,
        null,
        createElement(DocumentoDoAviso, { documento: { id: 7, titulo: 'Regimento interno' } }),
      ),
    )
    const link = screen.getByRole('link', { name: /Ver o documento.*Regimento interno/ })
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
    const link = await screen.findByRole('link', { name: /Ver documentos públicos/ })
    expect(link.getAttribute('href')).toBe('/documentos/publicos')
  })
})

// --- lista (H-18) ------------------------------------------------------------------------------

describe('lista de documentos', () => {
  const itens = [
    resumo(1, { titulo: 'Cronograma da obra', versao: 3 }),
    resumo(2, { titulo: 'Ata da reunião', categoria: 'ata', acesso: 'gestao' }),
    resumo(3, { titulo: 'Convenção do condomínio', categoria: 'convencao', acesso: 'publico' }),
  ]

  it('agrupa por assunto, com a data e a versão, e cada item abre o documento', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos': json(200, { itens }),
    })
    abrir('/documentos')
    await screen.findByRole('heading', { name: 'Obra' })
    // Só os da página: o menu lateral tem os títulos dos grupos ("Dia a dia").
    expect(within(screen.getByRole('main')).getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual([
      'Obra',
      'Convenção',
      'Atas',
    ])
    const item = screen.getByRole('link', { name: /Cronograma da obra/ })
    expect(item.getAttribute('href')).toBe('/documentos/1')
    expect(item.textContent).toContain('1 de outubro de 2026')
    expect(item.textContent).toContain('versão 3')
    expect(screen.queryByRole('link', { name: /Novo documento/ })).toBeNull()
    // O morador não vê os selos de quem vê (é assunto da gestão).
    expect(screen.getByRole('link', { name: /Convenção/ }).textContent).not.toContain('qualquer')
  })

  it('U15: para a gestão, selos "só a gestão vê" e "qualquer pessoa vê"', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['comissao'])),
      'GET /api/documentos': json(200, { itens }),
    })
    abrir('/documentos')
    const ata = await screen.findByRole('link', { name: /Ata da reunião/ })
    expect(ata.textContent).toContain('só a gestão vê')
    expect(screen.getByRole('link', { name: /Convenção/ }).textContent).toContain(
      'qualquer pessoa vê',
    )
    expect(screen.getByRole('link', { name: /Cronograma/ }).textContent).not.toMatch(/vê/)
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

  it('U16: os arquivados mostram quando foram arquivados', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, eu(['admin'])),
      'GET /api/documentos?arquivados=true': json(200, {
        itens: [resumo(4, { arquivado_em: '2026-10-05T12:00:00Z' })],
      }),
    })
    abrir('/documentos/arquivados')
    const item = await screen.findByRole('link', { name: /Documento 4/ })
    expect(item.textContent).toContain('arquivado em 5 de outubro de 2026')
    expect(chamadas.some((c) => c.caminho === '/api/documentos?arquivados=true')).toBe(true)
  })

  it('a unidade comum não abre os arquivados', async () => {
    apiFalsa({ 'GET /api/acesso/eu': json(200, eu()) })
    abrir('/documentos/arquivados')
    expect(await screen.findByText(/só da Comissão e da administração/)).toBeTruthy()
  })
})

// --- documento aberto (H-18, H-19) -------------------------------------------------------------

const ABRIR_2 = '/api/documentos/1/versoes/2/abrir'

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

  it('U7: abrir e baixar passam pelo Portal (link novo a cada toque)', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
    })
    abrir('/documentos/1')
    expect(await screen.findByRole('heading', { level: 2, name: 'Cronograma da obra' })).toBeTruthy()
    expect(screen.getByText(/PDF, 2,4 MB/)).toBeTruthy()
    expect(screen.getByText(/Versão 2/)).toBeTruthy()
    const abrirLink = screen.getByRole('link', { name: /Abrir o documento \(abre em outra aba\)/ })
    expect(abrirLink.getAttribute('href')).toBe(ABRIR_2)
    expect(abrirLink.getAttribute('target')).toBe('_blank')
    expect(abrirLink.getAttribute('rel')).toContain('noopener')
    const baixar = screen.getByRole('link', { name: /Baixar/ })
    expect(baixar.getAttribute('href')).toBe(`${ABRIR_2}?baixar=true`)
    expect(baixar.getAttribute('target')).toBeNull()
    expect(screen.queryByRole('link', { name: /Enviar nova versão/ })).toBeNull()
  })

  it('U17 (revisões do M5): o topo diz "Documento"; o título inteiro fica na folha e na aba', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
    })
    abrir('/documentos/1')
    await screen.findByRole('heading', { level: 2, name: 'Cronograma da obra' })
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Documento')
    expect(screen.getAllByText('Cronograma da obra')).toHaveLength(1)
    // O título da aba vem num useEffect da Tela: espera (2ª revisão do M5; falhava 2 em 8).
    await waitFor(() => expect(document.title).toBe('Cronograma da obra · Portal Capibaribe Prime'))
  })

  it('U12: o morador não vê "Quem vê"', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
    })
    abrir('/documentos/1')
    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByText(/Quem vê/)).toBeNull()
  })

  it('U4: o morador vê as versões anteriores recolhidas, com quando foram substituídas', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
    })
    abrir('/documentos/1')
    const resumoDasVersoes = await screen.findByText('Ver versões anteriores (1)')
    expect(resumoDasVersoes.closest('details')?.open).toBe(false)
    const secao = screen.getByRole('region', { name: /versões anteriores/i })
    expect(secao.textContent).toContain('Versão 1')
    expect(secao.textContent).toContain('enviada em 2 de outubro de 2026')
    expect(secao.textContent).toContain('Substituída pela versão 2 em 20 de outubro de 2026')
    const antiga = within(secao).getByRole('link', { name: /Abrir a versão 1/ })
    expect(antiga.getAttribute('href')).toBe('/api/documentos/1/versoes/1/abrir')
    expect(antiga.className).toContain('texto-link')
  })

  it('U7: o arquivo não abriu (arquivos desligados): a página diz por quê', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/1': json(200, comVersoes),
    })
    abrir('/documentos/1?erro=arquivos_desligados')
    expect(
      await screen.findByText(/O arquivo não abriu agora\. Tente de novo em alguns minutos/),
    ).toBeTruthy()
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

  it('para a gestão: quem vê, versões abertas, nova versão e arquivar com confirmação', async () => {
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
    expect(screen.getByRole('region', { name: 'Versões anteriores' })).toBeTruthy()
    expect(screen.getByText(/Quem vê: os apartamentos/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Arquivar' }))
    expect(chamadas.some((c) => c.metodo === 'POST')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: /Arquivar de vez/ }))
    expect(await screen.findByText(/Arquivado em 21 de outubro/)).toBeTruthy()
    expect(screen.queryByText(/Quem vê:/)).toBeNull()
    expect(screen.queryByRole('link', { name: /Enviar nova versão/ })).toBeNull()
  })
})

// --- documento público sem entrar (U2) ---------------------------------------------------------

describe('link de documento público sem entrar', () => {
  const publico = resumo(1, { titulo: 'Como acessar o Portal', categoria: 'orientacao', acesso: 'publico' })

  it('mostra o documento, com abrir, baixar e entrar', async () => {
    apiFalsa({ 'GET /api/documentos/publicos': json(200, { itens: [publico] }) })
    const roteador = abrir('/documentos/1')
    expect(await screen.findByRole('heading', { level: 2, name: 'Como acessar o Portal' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Documento')
    expect(roteador.state.location.pathname).toBe('/documentos/1')
    expect(
      screen.getByRole('link', { name: /Abrir o documento/ }).getAttribute('href'),
    ).toBe('/api/documentos/1/versoes/1/abrir')
    expect(screen.getByRole('link', { name: /Baixar/ })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Entrar' }).getAttribute('href')).toBe('/entrar')
  })

  it('documento que não é público: pede para entrar', async () => {
    apiFalsa({ 'GET /api/documentos/publicos': json(200, { itens: [publico] }) })
    const roteador = abrir('/documentos/2')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
  })
})

// --- públicos (H-18, U11) ----------------------------------------------------------------------

describe('documentos públicos', () => {
  const itens = [resumo(1, { titulo: 'Como acessar o Portal', categoria: 'orientacao', acesso: 'publico' })]

  it('sem entrar: cada um abre e baixa pelo Portal, e há o botão "Entrar"', async () => {
    apiFalsa({ 'GET /api/documentos/publicos': json(200, { itens }) })
    abrir('/documentos/publicos')
    expect(await screen.findByRole('heading', { name: 'Orientações' })).toBeTruthy()
    expect(screen.getByText(/aparecem depois que você entra/)).toBeTruthy()
    const abrirLink = screen.getByRole('link', { name: /Abrir Como acessar o Portal/ })
    expect(abrirLink.getAttribute('href')).toBe('/api/documentos/1/versoes/1/abrir')
    expect(abrirLink.getAttribute('target')).toBe('_blank')
    expect(
      screen.getByRole('link', { name: /Baixar Como acessar o Portal/ }).getAttribute('href'),
    ).toBe('/api/documentos/1/versoes/1/abrir?baixar=true')
    expect(screen.getByRole('link', { name: 'Entrar' }).getAttribute('href')).toBe('/entrar')
  })

  it('U11: já dentro do Portal, não manda entrar', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/documentos/publicos': json(200, { itens }),
    })
    abrir('/documentos/publicos')
    await screen.findByRole('heading', { name: 'Orientações' })
    expect(screen.queryByText(/aparecem depois que você entra/)).toBeNull()
    expect(screen.queryByRole('link', { name: 'Entrar' })).toBeNull()
    expect(
      screen.getByRole('link', { name: /Ver todos os documentos/ }).getAttribute('href'),
    ).toBe('/documentos')
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

function escolherArquivo(nome = 'regimento.pdf', conteudo = '%PDF-1.7', tipo = 'application/pdf') {
  const arquivo = new File([conteudo], nome, { type: tipo })
  fireEvent.change(screen.getByLabelText(/Escolher PDF ou foto|Trocar o arquivo/), {
    target: { files: [arquivo] },
  })
  return arquivo
}

/** Título, assunto e arquivo: o mínimo para publicar. */
async function preencher(titulo = 'Regimento interno', assunto = 'regimento') {
  fireEvent.change(await screen.findByLabelText('Título'), { target: { value: titulo } })
  fireEvent.change(screen.getByLabelText('Assunto'), { target: { value: assunto } })
  escolherArquivo()
}

/** A `apiFalsa` da casca lê todo corpo como JSON; o PUT do envio leva o arquivo. Aqui o corpo
 *  que não é JSON vira `undefined` antes de chegar nela. */
function apiDoEnvio(extra: Record<string, Response | ((corpo: unknown) => Response)> = {}) {
  const chamadas = apiFalsa({
    'GET /api/acesso/eu': json(200, eu(['comissao'])),
    'POST /api/arquivos': json(201, ENVIO),
    'PUT https://r2.falso/envios/abc': new Response(null, { status: 200 }),
    'POST /api/arquivos/42/confirmar': json(200, ENVIADO),
    'GET /api/documentos/5': json(200, documento(5, { titulo: 'Regimento interno' })),
    ...extra,
  })
  const falsa = globalThis.fetch as unknown as (c: string, o?: RequestInit) => Promise<Response>
  vi.stubGlobal(
    'fetch',
    vi.fn((caminho: string, opcoes?: RequestInit) =>
      falsa(caminho, typeof opcoes?.body === 'string' ? opcoes : { ...opcoes, body: undefined }),
    ),
  )
  return chamadas
}

describe('novo documento', () => {
  it('envia o arquivo, publica e abre o documento com a confirmação fixa (U9)', async () => {
    const chamadas = apiDoEnvio({
      'POST /api/documentos': json(201, documento(5, { titulo: 'Regimento interno', aviso_id: 3 })),
    })
    const roteador = abrir('/documentos/novo')
    await preencher()
    fireEvent.change(screen.getByLabelText('Data do documento'), {
      target: { value: '2026-10-05' },
    })
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
    expect(await screen.findByText(/Pronto: o documento foi publicado/)).toBeTruthy()
    expect(screen.getByText(/O aviso saiu no mural/)).toBeTruthy()
  })

  it('U13: linha opcional para o aviso, com a prévia de como ele fica', async () => {
    const chamadas = apiDoEnvio({ 'POST /api/documentos': json(201, documento(5)) })
    abrir('/documentos/novo')
    await preencher('Cronograma da obra', 'obra')
    fireEvent.change(screen.getByLabelText(/Uma linha para o aviso/), {
      target: { value: 'A entrega passou para março.' },
    })
    const previa = screen.getByRole('region', { name: 'Como o aviso vai ficar' })
    expect(previa.textContent).toContain('Documento novo: Cronograma da obra')
    expect(previa.textContent).toContain('A entrega passou para março.')
    expect(previa.textContent).toContain('Obra')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/documentos')?.corpo).toMatchObject({
        nota_do_aviso: 'A entrega passou para março.',
      }),
    )
  })

  it('"Só a gestão" tira a opção de avisar', async () => {
    const chamadas = apiDoEnvio({ 'POST /api/documentos': json(201, documento(5)) })
    abrir('/documentos/novo')
    await preencher('Ata', 'ata')
    fireEvent.click(screen.getByRole('radio', { name: /Só a gestão/ }))
    expect(screen.queryByRole('checkbox', { name: /Avisar/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/documentos')?.corpo).toMatchObject({
        acesso: 'gestao',
        avisar_unidades: false,
      }),
    )
  })

  it('U14: sem título, assunto ou arquivo: diz o que falta e não envia nada', async () => {
    const chamadas = apiDoEnvio()
    abrir('/documentos/novo')
    const assunto = (await screen.findByLabelText('Assunto')) as HTMLSelectElement
    expect(assunto.value).toBe('')
    expect(assunto.options[0].textContent).toBe('Escolha…')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    expect(await screen.findAllByText('Escreva o título do documento.')).not.toHaveLength(0)
    expect(screen.getAllByText('Escolha o assunto do documento.')).not.toHaveLength(0)
    expect(screen.getAllByText('Escolha o arquivo do documento.')).not.toHaveLength(0)
    expect(chamadas.filter((c) => c.metodo !== 'GET')).toEqual([])
  })

  it('U6: a ajuda do arquivo fala do documento de várias páginas', async () => {
    apiDoEnvio()
    abrir('/documentos/novo')
    expect(
      await screen.findByText(/Se o documento tem várias páginas, junte num PDF antes de enviar\./),
    ).toBeTruthy()
  })

  it('U10: confere o arquivo na hora de escolher, com o que fazer', async () => {
    apiDoEnvio()
    abrir('/documentos/novo')
    await screen.findByLabelText('Título')
    escolherArquivo(
      'regimento.docx',
      'PK',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    expect(screen.getAllByText(/Arquivo do Word: salve como PDF/).length).toBeGreaterThan(0)
    expect(screen.queryByText('regimento.docx')).toBeNull()
    const grande = new File(['%PDF'], 'grande.pdf', { type: 'application/pdf' })
    Object.defineProperty(grande, 'size', { value: 25 * MB })
    fireEvent.change(screen.getByLabelText(/Escolher PDF ou foto/), {
      target: { files: [grande] },
    })
    expect(screen.queryByText(/Arquivo do Word/)).toBeNull()
    expect(screen.getAllByText(/tem 25 MB e o limite é 20 MB\. Para reduzir/).length).toBeGreaterThan(0)
    escolherArquivo()
    expect(screen.queryByText(/limite é 20 MB/)).toBeNull()
    expect(screen.getByText('regimento.pdf')).toBeTruthy()
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
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    expect(await screen.findByText('O título pode ter até 120 letras.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(chamadas.filter((c) => c.caminho === '/api/arquivos')).toHaveLength(1)
  })

  it('U1: a resposta se perdeu e já estava publicado: leva ao documento, sem pedir o arquivo', async () => {
    let vez = 0
    const chamadas = apiDoEnvio({
      'POST /api/documentos': () =>
        ++vez === 1
          ? json(503, { codigo: 'sem_conexao', mensagem: 'Sem conexão com o Portal.' })
          : json(409, {
              codigo: 'arquivo_em_uso',
              mensagem: 'Este arquivo já está em outro documento. Escolha o arquivo de novo.',
              documento_id: 5,
              versao: 1,
            }),
    })
    const roteador = abrir('/documentos/novo')
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    expect(await screen.findAllByText('Sem conexão com o Portal.')).not.toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(await screen.findByText(/Já estava publicado/)).toBeTruthy()
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
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar documento' }))
    const erros = await screen.findAllByText(/não é um PDF nem uma foto/)
    expect(erros.length).toBeGreaterThan(0)
  })

  it('U5: sair com o formulário preenchido pede confirmação', async () => {
    apiDoEnvio()
    const roteador = abrir('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Regimento' } })
    const confirmar = vi.spyOn(window, 'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    await waitFor(() => expect(confirmar).toHaveBeenCalled())
    expect(roteador.state.location.pathname).toBe('/documentos/novo')
    confirmar.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos'))
  })

  it('U5: formulário vazio sai sem perguntar; preenchido avisa ao fechar a aba', async () => {
    apiDoEnvio()
    const roteador = abrir('/documentos/novo')
    const confirmar = vi.spyOn(window, 'confirm')
    fireEvent.click(await screen.findByRole('button', { name: 'Voltar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos'))
    expect(confirmar).not.toHaveBeenCalled()
    await roteador.navigate('/documentos/novo')
    fireEvent.change(await screen.findByLabelText('Título'), { target: { value: 'Ata' } })
    const evento = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(evento)
    expect(evento.defaultPrevented).toBe(true)
  })
})

describe('nova versão', () => {
  it('envia o arquivo e volta ao documento, sem aviso por padrão', async () => {
    const chamadas = apiDoEnvio({
      'GET /api/documentos/5': json(200, documento(5, { titulo: 'Regimento interno' })),
      'POST /api/documentos/5/versoes': json(201, documento(5, { versao: 2 })),
    })
    const roteador = abrir('/documentos/5/nova-versao')
    expect(await screen.findByText(/Regimento interno/)).toBeTruthy()
    const avisar = screen.getByRole('checkbox', { name: /Avisar os apartamentos/ }) as HTMLInputElement
    expect(avisar.checked).toBe(false)
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar nova versão' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(chamadas.find((c) => c.caminho === '/api/documentos/5/versoes')?.corpo).toEqual({
      arquivo_id: 42,
    })
    expect(await screen.findByText(/Pronto: a versão nova foi enviada/)).toBeTruthy()
  })

  it('U3: avisando, com o que mudou', async () => {
    const chamadas = apiDoEnvio({
      'GET /api/documentos/5': json(200, documento(5, { titulo: 'Regimento interno' })),
      'POST /api/documentos/5/versoes': json(201, documento(5, { versao: 2 })),
    })
    abrir('/documentos/5/nova-versao')
    fireEvent.click(await screen.findByRole('checkbox', { name: /Avisar os apartamentos/ }))
    fireEvent.change(screen.getByLabelText(/O que mudou/), {
      target: { value: 'Novo horário da piscina.' },
    })
    expect(screen.getByRole('region', { name: 'Como o aviso vai ficar' }).textContent).toContain(
      'Documento atualizado: Regimento interno',
    )
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar nova versão' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/documentos/5/versoes')?.corpo).toEqual({
        arquivo_id: 42,
        avisar_unidades: true,
        nota_do_aviso: 'Novo horário da piscina.',
      }),
    )
  })

  it('documento só da gestão: sem a opção de avisar', async () => {
    apiDoEnvio({
      'GET /api/documentos/5': json(200, documento(5, { acesso: 'gestao' })),
    })
    abrir('/documentos/5/nova-versao')
    await screen.findByRole('button', { name: 'Enviar nova versão' })
    expect(screen.queryByRole('checkbox', { name: /Avisar/ })).toBeNull()
  })

  it('U1: a versão já tinha ido: leva ao documento', async () => {
    apiDoEnvio({
      'POST /api/documentos/5/versoes': json(409, {
        codigo: 'arquivo_em_uso',
        mensagem: 'Este arquivo já está em outro documento. Escolha o arquivo de novo.',
        documento_id: 5,
        versao: 2,
      }),
    })
    const roteador = abrir('/documentos/5/nova-versao')
    await screen.findByRole('button', { name: 'Enviar nova versão' })
    escolherArquivo()
    fireEvent.click(screen.getByRole('button', { name: 'Enviar nova versão' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos/5'))
    expect(await screen.findByText(/Já estava enviada/)).toBeTruthy()
  })

  it('sem arquivo não envia', async () => {
    const chamadas = apiDoEnvio()
    abrir('/documentos/5/nova-versao')
    fireEvent.click(await screen.findByRole('button', { name: 'Enviar nova versão' }))
    expect(await screen.findAllByText('Escolha o arquivo da versão nova.')).not.toHaveLength(0)
    expect(chamadas.filter((c) => c.metodo !== 'GET')).toEqual([])
  })
})
