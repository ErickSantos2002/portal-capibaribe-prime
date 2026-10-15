// M4 · ajustes das revisões finais no formulário da enquete (épico A). Cada teste falhava antes
// da correção.
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import { createMemoryRouter } from 'react-router'
import { RouterProvider } from 'react-router/dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiFalsa, eu, json, type Chamada } from '../../acesso/apoioDeTeste'
import { rotas } from '../../rotas'
import { deIso, RASCUNHO_VAZIO, textoDoAviso } from './formatos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// Daqui a 10 dias: dentro do limite de 1 ano.
const DIA = deIso(new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString()).dia
const DESTINOS = { blocos: [1, 2].map((numero) => ({ numero, nome: `Bloco ${numero}` })) }

function apiDaGestao(extra: Parameters<typeof apiFalsa>[0] = {}): Chamada[] {
  return apiFalsa({
    'GET /api/acesso/eu': json(200, eu(['comissao'], false, '2304')),
    'GET /api/avisos/destinos': json(200, DESTINOS),
    'GET /api/avisos/alcance': json(200, { unidades: 320 }),
    ...extra,
  })
}

function abrir(caminho: string) {
  const roteador = createMemoryRouter(rotas, { initialEntries: ['/avisos', caminho], initialIndex: 1 })
  render(createElement(RouterProvider, { router: roteador }))
  return roteador
}

function escrever(rotulo: string, valor: string) {
  fireEvent.change(screen.getByLabelText(rotulo), { target: { value: valor } })
}

describe('5: id inválido no editar', () => {
  it('/enquetes/0/editar vai direto para "não encontrada", sem chamar a API', async () => {
    const chamadas = apiDaGestao()
    abrir('/enquetes/0/editar')
    expect(await screen.findByRole('heading', { name: 'Enquete não encontrada' })).toBeTruthy()
    expect(chamadas.some((c) => c.caminho.startsWith('/api/enquetes'))).toBe(false)
  })

  it('422 da API também é "não encontrada"', async () => {
    apiDaGestao({
      'GET /api/enquetes/7': json(422, {
        codigo: 'dados_invalidos',
        mensagem: 'Confira os dados enviados.',
        campos: [],
      }),
    })
    abrir('/enquetes/7/editar')
    expect(await screen.findByRole('heading', { name: 'Enquete não encontrada' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Tentar de novo' })).toBeNull()
  })

  it('404 da API também', async () => {
    apiDaGestao({
      'GET /api/enquetes/7': json(404, {
        codigo: 'enquete_nao_encontrada',
        mensagem: 'Não achamos esta enquete. O link pode estar incompleto, ou ela é de outro bloco.',
      }),
    })
    abrir('/enquetes/7/editar')
    expect(await screen.findByRole('heading', { name: 'Enquete não encontrada' })).toBeTruthy()
  })
})

describe('9: o erro geral some junto com o que o causou', () => {
  it('um campo só: corrigir o campo apaga o erro geral', async () => {
    apiDaGestao()
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    escrever('Pergunta', 'Qual o melhor dia?')
    escrever('Opção 1', 'Terça')
    escrever('Opção 2', 'Quinta')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Escolha o dia do término.')
    escrever('Dia do término', DIA)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('vários campos: some quando não sobra nenhum erro de campo', async () => {
    apiDaGestao()
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Confira os campos marcados.')
    escrever('Pergunta', 'Qual o melhor dia?')
    expect(screen.getByRole('alert')).toBeTruthy()
    escrever('Opção 1', 'Terça')
    escrever('Opção 2', 'Quinta')
    expect(screen.getByRole('alert')).toBeTruthy()
    escrever('Dia do término', DIA)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('o erro da API que não é de campo continua', async () => {
    apiDaGestao({
      'POST /api/enquetes': json(409, { codigo: 'tente_de_novo', mensagem: 'Tente de novo.' }),
    })
    abrir('/enquetes/nova')
    await screen.findByLabelText('Pergunta')
    escrever('Pergunta', 'Qual o melhor dia?')
    escrever('Opção 1', 'Terça')
    escrever('Opção 2', 'Quinta')
    escrever('Dia do término', DIA)
    fireEvent.click(screen.getByRole('button', { name: 'Publicar enquete' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Tente de novo.')
    escrever('Pergunta', 'Qual o melhor dia, afinal?')
    expect(screen.getByRole('alert')).toBeTruthy()
  })
})

describe('16: a data do aviso por extenso, como na enquete', () => {
  const AGORA = new Date('2026-10-14T12:00:00-03:00')
  const base = {
    ...RASCUNHO_VAZIO,
    pergunta: 'Qual o melhor dia?',
    opcoes: ['Terça', 'Quinta'],
  }

  it('no mesmo ano, sem o ano; com minutos, "às 19h30"', () => {
    expect(textoDoAviso({ ...base, dia: '2026-10-16', hora: '20:00' }, AGORA)).toContain(
      'Dá para votar até 16 de outubro, às 20h (horário de Recife).',
    )
    expect(textoDoAviso({ ...base, dia: '2026-10-16', hora: '19:30' }, AGORA)).toContain(
      'Dá para votar até 16 de outubro, às 19h30 (horário de Recife).',
    )
  })

  it('em outro ano, com o ano', () => {
    expect(textoDoAviso({ ...base, dia: '2027-01-05', hora: '12:00' }, AGORA)).toContain(
      'Dá para votar até 5 de janeiro de 2027, às 12h (horário de Recife).',
    )
  })
})
