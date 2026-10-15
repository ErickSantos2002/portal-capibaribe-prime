// Épico A do M4 · "Nova enquete" e "Editar enquete" com uma API de mentira (H-20, H-13).
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFalsa, eu, json, type Chamada } from '../../acesso/apoioDeTeste'
import { rotas } from '../../rotas'
import type { Enquete } from '../tipos'
import { deIso } from './formatos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

const DIA = 24 * 60 * 60 * 1000
// Daqui a 10 dias, no horário de Recife (o formulário confere "no futuro").
const DIA_DO_TERMINO = deIso(new Date(Date.now() + 10 * DIA).toISOString()).dia
const DESTINOS = {
  blocos: [1, 2, 3, 4, 5].map((numero) => ({ numero, nome: `Bloco ${numero}` })),
}

function apiDaGestao(extra: Parameters<typeof apiFalsa>[0] = {}): Chamada[] {
  return apiFalsa({
    'GET /api/acesso/eu': json(200, eu(['comissao'], false, '2304')),
    'GET /api/avisos/destinos': json(200, DESTINOS),
    'GET /api/avisos/alcance': json(200, { unidades: 320 }),
    'GET /api/avisos/alcance?blocos=1': json(200, { unidades: 64 }),
    ...extra,
  })
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: ['/avisos', caminho], initialIndex: 1 })
  render(createElement(RouterProvider, { router: roteador }))
  return roteador
}

function escrever(rotulo: string | RegExp, valor: string) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value: valor } })
}

function preencher() {
  escrever('Pergunta', 'Qual o melhor dia para a reunião?')
  escrever('Opção 1', 'Terça à noite')
  escrever('Opção 2', 'Quinta à noite')
  escrever('Dia do término', DIA_DO_TERMINO)
}

function enviados(chamadas: Chamada[], metodo: string) {
  return chamadas.filter((c) => c.metodo === metodo && c.caminho.startsWith('/api/enquetes'))
}

describe('nova enquete', () => {
  it('publica com o que a tela mostra e vai para a enquete, com o recado', async () => {
    const chamadas = apiDaGestao({ 'POST /api/enquetes': json(201, { id: 5, aviso_id: 9 }) })
    const roteador = abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/enquetes/5'))
    expect(enviados(chamadas, 'POST')[0].corpo).toEqual({
      pergunta: 'Qual o melhor dia para a reunião?',
      opcoes: ['Terça à noite', 'Quinta à noite'],
      multipla_escolha: false,
      encerra_em: `${DIA_DO_TERMINO}T20:00:00-03:00`,
      mostrar_resultado: 'durante',
      para_todos: true,
      blocos: [],
    })
    expect(roteador.state.location.state).toMatchObject({
      recado: 'Enquete publicada. O aviso saiu no mural.',
    })
  })

  it('múltipla escolha, só no fim e para um bloco', async () => {
    const chamadas = apiDaGestao({ 'POST /api/enquetes': json(201, { id: 5, aviso_id: 9 }) })
    abrir('/enquetes/nova')
    await screen.findByRole('button', { name: 'Bloco 1' })
    preencher()
    fireEvent.click(screen.getByRole('checkbox', { name: /Pode marcar mais de uma/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Só quando terminar/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Bloco 1' }))
    expect(await screen.findByText('64')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    await waitFor(() => expect(enviados(chamadas, 'POST')).toHaveLength(1))
    expect(enviados(chamadas, 'POST')[0].corpo).toMatchObject({
      multipla_escolha: true,
      mostrar_resultado: 'so_no_fim',
      para_todos: false,
      blocos: [1],
    })
  })

  it('a prévia mostra o aviso automático como vai sair no mural', async () => {
    apiDaGestao()
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    preencher()
    const previa = screen.getByRole('region', { name: 'Como o aviso vai ficar' })
    expect(previa.textContent).toContain('Enquete nova: Qual o melhor dia para a reunião?')
    expect(previa.textContent).toContain('Terça à noite')
    expect(previa.textContent).toContain('Não tem valor legal de votação em assembleia.')
    expect(previa.textContent).toContain('às 20h00 (horário de Recife)')
  })

  it('diz o que falta e não envia nada', async () => {
    const chamadas = apiDaGestao()
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    escrever('Opção 1', 'Sim')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getAllByText('Escreva a pergunta.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Escreva pelo menos 2 opções de resposta.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Escolha o dia do término.').length).toBeGreaterThan(0)
    expect(screen.getByLabelText('Pergunta').getAttribute('aria-invalid')).toBe('true')
    expect(enviados(chamadas, 'POST')).toHaveLength(0)
  })

  it('adicionar opção até 10, e tirar a partir da terceira', async () => {
    apiDaGestao()
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    expect(screen.queryByRole('button', { name: /Tirar a opção/ })).toBeNull()
    const adicionar = screen.getByRole('button', { name: 'Adicionar opção' })
    for (let i = 0; i < 8; i++) fireEvent.click(adicionar)
    expect(screen.getByLabelText('Opção 10')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Adicionar opção' })).toBeNull()
    expect(screen.getByText('O limite é de 10 opções.')).toBeTruthy()
    escrever('Opção 3', 'Terceira')
    escrever('Opção 4', 'Quarta')
    fireEvent.click(screen.getByRole('button', { name: 'Tirar a opção 3' }))
    expect((screen.getByLabelText('Opção 3') as HTMLInputElement).value).toBe('Quarta')
    expect(screen.queryByLabelText('Opção 10')).toBeNull()
    expect(screen.getByRole('button', { name: 'Adicionar opção' })).toBeTruthy()
  })

  it('erro da API marca o campo certo', async () => {
    apiDaGestao({
      'POST /api/enquetes': json(422, {
        codigo: 'dados_invalidos',
        mensagem: 'Duas opções estão iguais.',
        campos: [{ campo: 'opcoes', mensagem: 'Duas opções estão iguais.' }],
      }),
    })
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    preencher()
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByLabelText('Opção 1').getAttribute('aria-invalid')).toBe('true')
    expect(screen.getByRole('button', { name: 'Publicar enquete' })).toBeTruthy()
  })

  it('sair com algo escrito pergunta antes', async () => {
    apiDaGestao()
    const roteador = abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    escrever('Pergunta', 'Qual dia?')
    fireEvent.click(screen.getByRole('button', { name: 'Voltar' }))
    const pergunta = await screen.findByRole('alertdialog', { name: 'Sair sem publicar?' })
    fireEvent.click(within(pergunta).getByRole('button', { name: 'Continuar escrevendo' }))
    expect(roteador.state.location.pathname).toBe('/enquetes/nova')
  })

  it('o alerta do primeiro voto está no formulário', async () => {
    apiDaGestao()
    abrir('/enquetes/nova')
    expect(
      await screen.findByText('Depois do primeiro voto, a pergunta e as opções não podem mais mudar.'),
    ).toBeTruthy()
  })

  it('a unidade comum não vê o formulário', async () => {
    apiFalsa({ 'GET /api/acesso/eu': json(200, eu()) })
    abrir('/enquetes/nova')
    expect(await screen.findByText(/só da Comissão e da administração/)).toBeTruthy()
    expect(screen.queryByLabelText('Pergunta')).toBeNull()
  })
})

// --- editar ------------------------------------------------------------------------------------

function enquete(extra: Partial<Enquete> = {}): Enquete {
  return {
    id: 7,
    pergunta: 'Qual o melhor dia?',
    multipla_escolha: false,
    mostrar_resultado: 'durante',
    encerra_em: `${DIA_DO_TERMINO}T23:30:00Z`,
    encerrada: false,
    para_todos: false,
    blocos: [1, 3],
    criada_em: '2026-10-14T12:00:00Z',
    editada_em: null,
    ja_votou: false,
    opcoes: [
      { id: 71, texto: 'Sábado', votos: 0 },
      { id: 72, texto: 'Domingo', votos: 0 },
    ],
    meu_voto: [],
    votado_em: null,
    participacao: { votaram: 0, total: 128 },
    resultado_visivel: true,
    pode_votar: true,
    pode_editar: true,
    aviso_id: 9,
    ...extra,
  }
}

describe('editar enquete', () => {
  it('carrega o que está gravado, salva e volta para a enquete', async () => {
    const chamadas = apiDaGestao({
      'GET /api/enquetes/7': json(200, enquete()),
      'PUT /api/enquetes/7': json(200, { id: 7, aviso_id: 9 }),
    })
    const roteador = abrir('/enquetes/7/editar')
    const pergunta = (await screen.findByLabelText('Pergunta')) as HTMLInputElement
    expect(pergunta.value).toBe('Qual o melhor dia?')
    expect((screen.getByLabelText('Opção 2') as HTMLInputElement).value).toBe('Domingo')
    expect((screen.getByLabelText('Hora do término') as HTMLInputElement).value).toBe('20:30')
    // O destino não muda: aparece escrito, sem botões.
    expect(screen.getByText(/Blocos 1 e 3/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Bloco 1' })).toBeNull()
    escrever('Opção 2', 'Domingo de manhã')
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/enquetes/7'))
    expect(enviados(chamadas, 'PUT')[0].corpo).toEqual({
      pergunta: 'Qual o melhor dia?',
      opcoes: ['Sábado', 'Domingo de manhã'],
      multipla_escolha: false,
      encerra_em: `${DIA_DO_TERMINO}T20:30:00-03:00`,
      mostrar_resultado: 'durante',
    })
    expect(roteador.state.location.state).toMatchObject({
      recado: 'Enquete atualizada. O aviso foi corrigido.',
    })
  })

  it('com voto: explica por que não edita e leva à enquete', async () => {
    apiDaGestao({ 'GET /api/enquetes/7': json(200, enquete({ pode_editar: false })) })
    abrir('/enquetes/7/editar')
    expect(
      await screen.findByText(/A enquete já recebeu votos: a pergunta e as opções não podem mais mudar/),
    ).toBeTruthy()
    expect(screen.queryByLabelText('Pergunta')).toBeNull()
    expect(screen.getByRole('link', { name: 'Ver a enquete' }).getAttribute('href')).toBe(
      '/enquetes/7',
    )
  })

  it('terminada: explica que nada muda', async () => {
    apiDaGestao({
      'GET /api/enquetes/7': json(200, enquete({ pode_editar: false, encerrada: true })),
    })
    abrir('/enquetes/7/editar')
    expect(await screen.findByText(/Esta enquete já terminou/)).toBeTruthy()
  })

  it('alguém votou enquanto editava: a frase da API e o link', async () => {
    apiDaGestao({
      'GET /api/enquetes/7': json(200, enquete()),
      'PUT /api/enquetes/7': json(409, {
        codigo: 'enquete_com_voto',
        mensagem: 'A enquete já recebeu votos: a pergunta e as opções não podem mais mudar.',
      }),
    })
    abrir('/enquetes/7/editar')
    await screen.findByLabelText('Pergunta')
    escrever('Pergunta', 'Outra pergunta?')
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toContain('A enquete já recebeu votos')
    expect(within(alerta).getByRole('link', { name: 'Ver a enquete' })).toBeTruthy()
  })

  it('enquete que não existe', async () => {
    apiDaGestao({
      'GET /api/enquetes/7': json(404, {
        codigo: 'enquete_nao_encontrada',
        mensagem: 'Enquete não encontrada.',
      }),
    })
    abrir('/enquetes/7/editar')
    expect(await screen.findByText(/Não achamos esta página/)).toBeTruthy()
  })
})
