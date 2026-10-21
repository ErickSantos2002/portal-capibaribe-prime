// Classificados · anunciar e editar (spec, seção 3.3): o tipo sem padrão, o preço só na venda, o
// contato que começa com o celular da unidade, as fotos (até 4, enviadas na hora, com "Tirar") e
// "Sair sem publicar?".
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ErroDaApi } from '../api/cliente'
import { abrir, eu, json } from '../acesso/apoioDeTeste'
import { anuncio, apiClassificados } from './apoioDeTeste'

// O envio de cada foto (pedir, PUT, confirmar) é testado em fotos.test.ts; aqui, só a tela.
const enviarFoto = vi.hoisted(() => vi.fn())
vi.mock('./fotos', async (original) => ({
  ...(await original<typeof import('./fotos')>()),
  enviarFoto,
}))

const MORADOR = eu([], false, '2304')

beforeEach(() => {
  let n = 0
  URL.createObjectURL = vi.fn(() => `blob:foto-${++n}`)
  URL.revokeObjectURL = vi.fn()
  let id = 40
  enviarFoto.mockReset()
  enviarFoto.mockImplementation(async (arquivo: File) => {
    if (!arquivo.type.startsWith('image/')) {
      throw new ErroDaApi(422, {
        codigo: 'dados_invalidos',
        mensagem: 'O Portal aceita fotos em JPEG, PNG ou WEBP.',
      })
    }
    return ++id
  })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const MINHA_UNIDADE = json(200, {
  unidade: { login: '2304', bloco: 2, apartamento: '304' },
  responsavel_nome: 'Fictício',
  celular: '81900000001',
  email: null,
  receber_avisos_email: true,
  papeis: [],
  ativada_em: '2026-10-01T12:00:00Z',
  aparelhos: [],
})

function foto(nome = 'sofa.jpg') {
  return new File([new Uint8Array([0xff, 0xd8, 0xff, 1, 2, 3])], nome, { type: 'image/jpeg' })
}

function comFotos(extra: Record<string, Response | ((corpo: unknown) => Response)> = {}) {
  return apiClassificados(MORADOR, { 'GET /api/minha-unidade': MINHA_UNIDADE, ...extra })
}

async function preencher(tipo = 'Vender') {
  fireEvent.click(await screen.findByLabelText(tipo))
  fireEvent.change(screen.getByLabelText('Categoria'), { target: { value: '1' } })
  fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Sofá de 3 lugares' } })
}

describe('anunciar', () => {
  it('o contato começa com o celular da unidade, com a frase de quem vê', async () => {
    comFotos()
    abrir('/classificados/novo')
    const contato = (await screen.findByLabelText('WhatsApp ou telefone para contato')) as HTMLInputElement
    expect(contato.value).toBe('(81) 9 0000-0001')
    expect(screen.getByText('Aparece para os vizinhos logados neste anúncio.')).toBeTruthy()
    expect(screen.getByText(/Evite fotos com pessoas ou documentos/)).toBeTruthy()
  })

  it('não publica sem escolher vender, trocar ou doar, sem categoria e sem título', async () => {
    const chamadas = comFotos()
    abrir('/classificados/novo')
    fireEvent.click(await screen.findByRole('button', { name: 'Publicar anúncio' }))
    expect(screen.getByRole('alert').textContent).toContain('Confira os campos marcados.')
    expect(screen.getByText('Escolha se você quer vender, trocar ou doar.')).toBeTruthy()
    expect(screen.getByText('Escolha a categoria.')).toBeTruthy()
    expect(screen.getByText('Escreva o que você está anunciando.')).toBeTruthy()
    expect(chamadas.some((c) => c.metodo === 'POST' && c.caminho === '/api/classificados')).toBe(false)
  })

  it('o preço só aparece em Vender; vazio é "a combinar" (nulo)', async () => {
    const chamadas = comFotos({ 'POST /api/classificados': json(201, { id: 9 }) })
    abrir('/classificados/novo')
    await preencher('Doar')
    expect(screen.queryByLabelText('Preço (opcional)')).toBeNull()
    fireEvent.click(screen.getByLabelText('Vender'))
    expect(screen.getByLabelText('Preço (opcional)')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/classificados')?.corpo).toEqual({
        tipo: 'venda',
        categoria_id: 1,
        titulo: 'Sofá de 3 lugares',
        descricao: null,
        preco_centavos: null,
        contato: '(81) 9 0000-0001',
        fotos: [],
      }),
    )
  })

  it('preço com vírgula vira centavos; preço inválido não publica', async () => {
    const chamadas = comFotos({ 'POST /api/classificados': json(201, { id: 9 }) })
    abrir('/classificados/novo')
    await preencher()
    fireEvent.change(screen.getByLabelText('Preço (opcional)'), { target: { value: 'barato' } })
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    expect(screen.getAllByText(/Escreva o preço em reais/).length).toBeGreaterThan(0)
    fireEvent.change(screen.getByLabelText('Preço (opcional)'), { target: { value: '1.250,50' } })
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    await waitFor(() =>
      expect(
        (chamadas.find((c) => c.caminho === '/api/classificados')?.corpo as { preco_centavos: number })
          ?.preco_centavos,
      ).toBe(125050),
    )
  })

  it('as fotos são enviadas na hora, a primeira é a capa, e "Tirar" tira', async () => {
    const chamadas = comFotos({ 'POST /api/classificados': json(201, { id: 9 }) })
    abrir('/classificados/novo')
    await preencher()
    const campo = screen.getByLabelText(/Escolher fotos/) as HTMLInputElement
    fireEvent.change(campo, { target: { files: [foto('a.jpg'), foto('b.jpg')] } })
    await waitFor(() => expect(screen.getAllByText(/Capa|Foto 2/).length).toBe(2))
    const fotos = screen.getByRole('group', { name: /Fotos/ })
    expect(within(fotos).getByText('Capa')).toBeTruthy()
    expect(enviarFoto).toHaveBeenCalledTimes(2)
    fireEvent.click(within(fotos).getAllByRole('button', { name: /Tirar/ })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    await waitFor(() =>
      expect(
        (chamadas.find((c) => c.caminho === '/api/classificados')?.corpo as { fotos: number[] })?.fotos,
      ).toEqual([42]),
    )
  })

  it('foto que não é imagem mostra a frase e não deixa publicar', async () => {
    comFotos()
    abrir('/classificados/novo')
    await preencher()
    const pdf = new File(['%PDF'], 'conta.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText(/Escolher fotos/), { target: { files: [pdf] } })
    expect(await screen.findByText('O Portal aceita fotos em JPEG, PNG ou WEBP.')).toBeTruthy()
    expect(enviarFoto).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    expect(screen.getAllByText(/Uma foto não foi enviada/).length).toBeGreaterThan(0)
  })

  it('publicar vai para o anúncio criado com o recado', async () => {
    comFotos({
      'POST /api/classificados': json(201, { id: 9 }),
      'GET /api/classificados/9': json(200, anuncio({ id: 9, meu: true })),
    })
    const roteador = abrir('/classificados/novo')
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/classificados/9'))
  })

  it('erro de campo da API vai para o campo', async () => {
    comFotos({
      'POST /api/classificados': json(422, {
        codigo: 'dados_invalidos',
        mensagem: 'Só a venda tem preço.',
        campos: [{ campo: 'preco_centavos', mensagem: 'Só a venda tem preço.' }],
      }),
    })
    abrir('/classificados/novo')
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar anúncio' }))
    expect(await screen.findAllByText('Só a venda tem preço.')).toHaveLength(2)
  })

  it('sair com algo escrito pergunta "Sair sem publicar?"', async () => {
    comFotos({ 'GET /api/classificados': json(200, { itens: [], com_aviso: null, meus: 0 }) })
    abrir('/classificados/novo')
    await preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    expect(await screen.findByRole('alertdialog', { name: 'Sair sem publicar?' })).toBeTruthy()
    expect(screen.getByText('O que você escreveu e as fotos que escolheu vão se perder.')).toBeTruthy()
  })
})

describe('revisão de UX', () => {
  it('11: já no limite, o aviso aparece ao abrir, antes do Publicar', async () => {
    comFotos({
      'GET /api/classificados/meus': json(200, {
        itens: [],
        limite: 'Seu apartamento já fez 5 anúncios hoje. Tente de novo amanhã.',
      }),
    })
    abrir('/classificados/novo')
    expect(
      await screen.findByText('Seu apartamento já fez 5 anúncios hoje. Tente de novo amanhã.'),
    ).toBeTruthy()
  })

  it('15: o exemplo do título é curto (não corta a 360 px com a letra a 150 %)', async () => {
    comFotos()
    abrir('/classificados/novo')
    const titulo = (await screen.findByLabelText('Título')) as HTMLInputElement
    expect(titulo.placeholder.length).toBeLessThanOrEqual(20)
  })
})

describe('editar', () => {
  it('começa com o que o anúncio tem, as fotos inclusive, e salva com PUT', async () => {
    const chamadas = comFotos({
      'GET /api/classificados/7': json(200, anuncio({ meu: true })),
      'PUT /api/classificados/7': json(200, anuncio({ meu: true })),
    })
    const roteador = abrir('/classificados/7/editar')
    const titulo = (await screen.findByLabelText('Título')) as HTMLInputElement
    expect(titulo.value).toBe('Sofá de 3 lugares')
    expect((screen.getByLabelText('Preço (opcional)') as HTMLInputElement).value).toBe('350')
    expect((screen.getByLabelText('Vender') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('WhatsApp ou telefone para contato') as HTMLInputElement).value).toBe(
      '(81) 9 9999-0001',
    )
    const fotos = screen.getByRole('group', { name: /Fotos/ })
    fireEvent.click(within(fotos).getAllByRole('button', { name: /Tirar/ })[1])
    fireEvent.click(screen.getByRole('button', { name: 'Salvar as mudanças' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/classificados/7'))
    const corpo = chamadas.find((c) => c.metodo === 'PUT' && c.caminho === '/api/classificados/7')
      ?.corpo as { fotos: number[]; preco_centavos: number }
    expect(corpo.fotos).toEqual([11])
    expect(corpo.preco_centavos).toBe(35000)
  })

  it('quem não é o dono vê que não pode mudar', async () => {
    comFotos({ 'GET /api/classificados/7': json(200, anuncio({ meu: false })) })
    abrir('/classificados/7/editar')
    expect(await screen.findByText('Só o apartamento que anunciou pode mudar este anúncio.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Salvar as mudanças' })).toBeNull()
  })
})
