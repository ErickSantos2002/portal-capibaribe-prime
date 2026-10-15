// Épico B do M4 · telas de votar e ver o resultado (H-21, H-22) com uma API de mentira: cada
// critério de aceite que aparece na tela.
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../../acesso/apoioDeTeste'
import type { Enquete, EnqueteResumo, Votantes } from '../tipos'
import { EnqueteDoAviso } from './EnqueteDoAviso'
import { itemEnquetes } from './menu'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

// Fim em 10/11/2099 às 20h de Recife: sempre "aberta" e em outro ano que o de hoje.
const FIM = '2099-11-10T23:00:00Z'
const FIM_TEXTO = '10 de novembro de 2099, às 20h'

function resumo(id: number, extra: Partial<EnqueteResumo> = {}): EnqueteResumo {
  return {
    id,
    pergunta: `Pergunta ${id}?`,
    multipla_escolha: false,
    mostrar_resultado: 'durante',
    encerra_em: FIM,
    encerrada: false,
    para_todos: true,
    blocos: [],
    criada_em: '2026-11-01T12:00:00Z',
    editada_em: null,
    ja_votou: false,
    ...extra,
  }
}

function enquete(extra: Partial<Enquete> = {}): Enquete {
  return {
    ...resumo(7, { pergunta: 'Qual o melhor dia para a reunião?' }),
    opcoes: [
      { id: 21, texto: 'Terça à noite', votos: 41 },
      { id: 22, texto: 'Quinta à noite', votos: 63 },
      { id: 23, texto: 'Sábado de manhã', votos: 88 },
    ],
    meu_voto: [],
    votado_em: null,
    participacao: { votaram: 192, total: 320 },
    resultado_visivel: true,
    pode_votar: true,
    pode_editar: false,
    aviso_id: 40,
    ...extra,
  }
}

const COMUM = eu()
const COMISSAO = eu(['comissao'], false, '2304')

// --- menu e aviso ------------------------------------------------------------------------------

describe('encaixes', () => {
  it('"Enquetes" no menu para toda unidade', () => {
    for (const quem of [COMUM, COMISSAO]) {
      expect(itemEnquetes(quem)).toEqual({ para: '/enquetes', icone: 'enquetes', texto: 'Enquetes' })
    }
  })

  it('o aviso automático leva para a enquete', () => {
    render(
      createElement(
        MemoryRouter,
        null,
        createElement(EnqueteDoAviso, { enquete: { id: 3, pergunta: 'Qual o melhor dia?' } }),
      ),
    )
    const link = screen.getByRole('link', { name: /Ir para a enquete/ })
    expect(link.getAttribute('href')).toBe('/enquetes/3')
    expect(link.textContent).toContain('Qual o melhor dia?')
  })

  it('aviso sem enquete não mostra nada', () => {
    const { container } = render(createElement(EnqueteDoAviso, { enquete: null }))
    expect(container.innerHTML).toBe('')
  })
})

// --- lista ---------------------------------------------------------------------------------------

describe('lista de enquetes', () => {
  const itens = [
    resumo(1, { pergunta: 'Aberta sem voto?' }),
    resumo(2, { pergunta: 'Aberta votada?', ja_votou: true }),
    resumo(3, { pergunta: 'Só do Bloco 2?', para_todos: false, blocos: [2] }),
    resumo(4, { pergunta: 'Terminada?', encerrada: true, encerra_em: '2026-09-20T23:00:00Z' }),
  ]

  it('abertas e terminadas, com o selo de quem ainda não votou', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes': json(200, { itens }),
    })
    abrir('/enquetes')
    const abertas = await screen.findByRole('region', { name: 'Abertas' })
    const terminadas = screen.getByRole('region', { name: 'Terminadas' })
    const link = (nome: string) => screen.getByRole('link', { name: new RegExp(nome) })
    expect(within(abertas).getAllByRole('link').map((l) => l.getAttribute('href'))).toEqual([
      '/enquetes/1',
      '/enquetes/2',
      '/enquetes/3',
    ])
    expect(within(terminadas).getAllByRole('link').map((l) => l.getAttribute('href'))).toEqual([
      '/enquetes/4',
    ])
    // A Comissão (Bloco 2) não votou na 1 e na 3; a 2 já votou.
    expect(link('Aberta sem voto').textContent).toContain('Seu apartamento ainda não votou')
    expect(link('Só do Bloco 2').textContent).toContain('Seu apartamento ainda não votou')
    expect(link('Aberta votada').textContent).not.toContain('ainda não votou')
    expect(link('Aberta votada').textContent).toContain('Seu apartamento já votou')
    expect(link('Aberta sem voto').textContent).toContain(`Vai até ${FIM_TEXTO}`)
    expect(link('Terminada').textContent).toContain('Terminou em 20 de setembro')
    expect(link('Terminada').textContent).not.toContain('votou')
  })

  it('gestão fora do destino não leva o selo: não vota nela', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes': json(200, { itens: [resumo(5, { para_todos: false, blocos: [1] })] }),
    })
    abrir('/enquetes')
    const item = await screen.findByRole('link', { name: /Pergunta 5/ })
    expect(item.textContent).not.toContain('ainda não votou')
    expect(item.textContent).toContain('Para o Bloco 1')
  })

  it('"Nova enquete" só para a gestão', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes': json(200, { itens: [] }),
    })
    abrir('/enquetes')
    const nova = await screen.findByRole('link', { name: /Nova enquete/ })
    expect(nova.getAttribute('href')).toBe('/enquetes/nova')
    expect(await screen.findByText('Nenhuma enquete aberta agora.')).toBeTruthy()
    cleanup()
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes': json(200, { itens: [] }),
    })
    abrir('/enquetes')
    await screen.findByText('Nenhuma enquete aberta agora.')
    expect(screen.queryByRole('link', { name: /Nova enquete/ })).toBeNull()
  })

  it('falha ao carregar: tentar de novo', async () => {
    let vez = 0
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes': () =>
        vez++ === 0
          ? json(500, { codigo: 'erro_interno', mensagem: 'Algo deu errado.' })
          : json(200, { itens: [resumo(1)] }),
    })
    abrir('/enquetes')
    fireEvent.click(await screen.findByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByRole('link', { name: /Pergunta 1/ })).toBeTruthy()
  })
})

// --- votar ---------------------------------------------------------------------------------------

describe('votar (H-21)', () => {
  it('escolher e votar, com a confirmação no lugar', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
      'PUT /api/enquetes/7/voto': json(
        200,
        enquete({ meu_voto: [22], ja_votou: true, votado_em: '2026-11-03T12:00:00Z' }),
      ),
    })
    abrir('/enquetes/7')
    expect(await screen.findByRole('heading', { name: 'Qual o melhor dia para a reunião?' })).toBeTruthy()
    expect(
      screen.getByText(
        `O voto vale pelo apartamento 203 do Bloco 1. Dá para trocar até ${FIM_TEXTO}.`,
      ),
    ).toBeTruthy()
    const votar = screen.getByRole('button', { name: 'Votar' }) as HTMLButtonElement
    expect(votar.disabled).toBe(true)
    expect(screen.getByText('Escolha uma opção para votar.')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Quinta à noite' }))
    expect(votar.disabled).toBe(false)
    expect(screen.queryByText('Escolha uma opção para votar.')).toBeNull()
    fireEvent.click(votar)
    const confirmacao = await screen.findByRole('region', { name: 'Seu voto' })
    expect(confirmacao.textContent).toBe(
      'Voto registrado. Seu apartamento já votou em Quinta à noite. Se escolher outra, vale a nova.',
    )
    await waitFor(() => expect(document.activeElement).toBe(confirmacao))
    expect(chamadas.find((c) => c.metodo === 'PUT')).toMatchObject({
      caminho: '/api/enquetes/7/voto',
      corpo: { opcoes: [22] },
    })
    expect(screen.getByRole('button', { name: 'Trocar voto' })).toBeTruthy()
  })

  it('quem já votou vê o voto da unidade e troca', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete({ meu_voto: [21], ja_votou: true })),
      'PUT /api/enquetes/7/voto': json(200, enquete({ meu_voto: [23], ja_votou: true })),
    })
    abrir('/enquetes/7')
    const status = await screen.findByRole('region', { name: 'Seu voto' })
    expect(status.textContent).toBe(
      'Seu apartamento já votou em Terça à noite. Se escolher outra, vale a nova.',
    )
    expect((screen.getByRole('radio', { name: 'Terça à noite' }) as HTMLInputElement).checked).toBe(true)
    const trocar = screen.getByRole('button', { name: 'Trocar voto' }) as HTMLButtonElement
    // A mesma escolha de antes: nada a trocar.
    expect(trocar.disabled).toBe(true)
    expect(screen.getByText('Para trocar o voto, escolha outra opção.')).toBeTruthy()
    fireEvent.click(screen.getByRole('radio', { name: 'Sábado de manhã' }))
    fireEvent.click(trocar)
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Seu voto' }).textContent).toContain('já votou em Sábado de manhã'),
    )
    expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({ opcoes: [23] })
  })

  it('múltipla escolha com caixas, na ordem das opções', async () => {
    const chamadas = apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete({ multipla_escolha: true })),
      'PUT /api/enquetes/7/voto': json(200, enquete({ multipla_escolha: true, meu_voto: [21, 23] })),
    })
    abrir('/enquetes/7')
    expect(await screen.findByText('Pode marcar mais de uma.')).toBeTruthy()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Sábado de manhã' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Terça à noite' }))
    fireEvent.click(screen.getByRole('button', { name: 'Votar' }))
    await waitFor(() =>
      expect(screen.getByRole('region', { name: 'Seu voto' }).textContent).toContain(
        'já votou em Terça à noite e Sábado de manhã',
      ),
    )
    expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({ opcoes: [21, 23] })
  })

  it('erro ao votar aparece no lugar e a escolha não se perde', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
      'PUT /api/enquetes/7/voto': json(409, {
        codigo: 'enquete_encerrada',
        mensagem: 'Esta enquete já terminou: o voto não pode mais ser dado nem trocado.',
      }),
    })
    abrir('/enquetes/7')
    fireEvent.click(await screen.findByRole('radio', { name: 'Terça à noite' }))
    fireEvent.click(screen.getByRole('button', { name: 'Votar' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Esta enquete já terminou')
    expect((screen.getByRole('radio', { name: 'Terça à noite' }) as HTMLInputElement).checked).toBe(true)
    expect(screen.queryByRole('region', { name: 'Seu voto' })).toBeNull()
  })

  it('"enquete mudou": recarrega para mostrar as opções de agora', async () => {
    let vez = 0
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': () =>
        json(
          200,
          vez++ === 0
            ? enquete()
            : enquete({ opcoes: [{ id: 31, texto: 'Domingo à tarde', votos: 0 }, ...enquete().opcoes.slice(1)] }),
        ),
      'PUT /api/enquetes/7/voto': json(409, {
        codigo: 'enquete_mudou',
        mensagem: 'A enquete mudou agora há pouco. Abra de novo e confira as opções.',
      }),
    })
    abrir('/enquetes/7')
    fireEvent.click(await screen.findByRole('radio', { name: 'Terça à noite' }))
    fireEvent.click(screen.getByRole('button', { name: 'Votar' }))
    expect(await screen.findByRole('radio', { name: 'Domingo à tarde' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('A enquete mudou')
  })
})

// --- resultado -----------------------------------------------------------------------------------

describe('resultado (H-22)', () => {
  it('durante: barras com votos e porcentagem, e a participação', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
    })
    abrir('/enquetes/7')
    const resultado = await screen.findByRole('region', { name: 'Como está até agora' })
    expect(within(resultado).getByText('88 votos, 46%')).toBeTruthy()
    expect(within(resultado).getByText('41 votos, 21%')).toBeTruthy()
    expect(within(resultado).getByText('192 de 320 apartamentos votaram (60%).')).toBeTruthy()
    const barra = within(resultado).getByRole('meter', { name: 'Sábado de manhã' })
    expect(barra.getAttribute('aria-valuenow')).toBe('46')
  })

  it('só no fim: só a participação, e quando o resultado aparece', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({
          mostrar_resultado: 'so_no_fim',
          resultado_visivel: false,
          opcoes: enquete().opcoes.map((o) => ({ ...o, votos: null })),
        }),
      ),
    })
    abrir('/enquetes/7')
    const resultado = await screen.findByRole('region', { name: 'Resultado' })
    expect(resultado.textContent).toContain(
      `O resultado aparece quando a enquete terminar, em ${FIM_TEXTO}. Até lá, ninguém vê os votos, nem a Comissão.`,
    )
    expect(resultado.textContent).toContain('192 de 320 apartamentos votaram (60%).')
    expect(within(resultado).queryByRole('meter')).toBeNull()
  })

  it('terminada: sem votar, com o resultado final', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({ encerrada: true, encerra_em: '2026-09-20T23:00:00Z', pode_votar: false, meu_voto: [22] }),
      ),
    })
    abrir('/enquetes/7')
    expect((await screen.findByText(/Terminou em 20 de setembro/)).textContent).toContain(
      'O resultado não muda mais.',
    )
    expect(screen.getByText(/Seu apartamento votou em Quinta à noite/)).toBeTruthy()
    expect(screen.queryByRole('radio')).toBeNull()
    expect(screen.queryByRole('button', { name: /Votar|Trocar/ })).toBeNull()
    expect(screen.getByRole('region', { name: 'Resultado' })).toBeTruthy()
  })

  it('toda enquete lembra que é consulta (RN-03)', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
    })
    abrir('/enquetes/7')
    expect(
      await screen.findByText('Enquete é consulta. Não tem valor legal de votação em assembleia.'),
    ).toBeTruthy()
  })

  it('enquete que não existe ou é de outro bloco', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(404, {
        codigo: 'enquete_nao_encontrada',
        mensagem: 'Não achamos esta enquete. O link pode estar incompleto, ou ela é de outro bloco.',
      }),
    })
    abrir('/enquetes/7')
    expect(await screen.findByRole('heading', { name: 'Enquete não encontrada' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ir para as enquetes' }).getAttribute('href')).toBe('/enquetes')
  })
})

// --- gestão --------------------------------------------------------------------------------------

describe('para a Comissão', () => {
  it('"Quais apartamentos votaram" e "Editar" enquanto ninguém votou', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ pode_editar: true })),
    })
    abrir('/enquetes/7')
    const votantes = await screen.findByRole('link', { name: /Quais apartamentos votaram/ })
    expect(votantes.getAttribute('href')).toBe('/enquetes/7/votantes')
    expect(screen.getByRole('link', { name: /Editar a enquete/ }).getAttribute('href')).toBe(
      '/enquetes/7/editar',
    )
  })

  it('sem "Editar" depois do primeiro voto; o morador não vê nada disso', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ pode_editar: false })),
    })
    abrir('/enquetes/7')
    await screen.findByRole('link', { name: /Quais apartamentos votaram/ })
    expect(screen.queryByRole('link', { name: /Editar a enquete/ })).toBeNull()
    cleanup()
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
    })
    abrir('/enquetes/7')
    await screen.findByRole('button', { name: 'Votar' })
    expect(screen.queryByRole('link', { name: /Quais apartamentos votaram/ })).toBeNull()
  })

  it('gestão fora do destino vê, mas não vota', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ para_todos: false, blocos: [1], pode_votar: false })),
    })
    abrir('/enquetes/7')
    expect(
      await screen.findByText('Esta enquete é para o Bloco 1. Seu apartamento não vota nela.'),
    ).toBeTruthy()
    expect(screen.queryByRole('radio')).toBeNull()
  })

  it('quais apartamentos votaram, sem dizer em quê', async () => {
    const lista: Votantes = {
      votaram: [{ login: '1203', bloco: 1, apartamento: '203' }],
      entraram_sem_votar: [{ login: '1101', bloco: 1, apartamento: '101' }],
      nao_entraram: [
        { login: '1102', bloco: 1, apartamento: '102' },
        { login: '1701', bloco: 1, apartamento: '701' },
      ],
    }
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ participacao: { votaram: 1, total: 4 } })),
      'GET /api/enquetes/7/votantes': json(200, lista),
    })
    abrir('/enquetes/7/votantes')
    expect(await screen.findByText('1 de 4 apartamentos votou (25%).')).toBeTruthy()
    const votaram = screen.getByRole('region', { name: 'Votaram (1)' })
    expect(within(votaram).getByLabelText('Bloco 1, apartamento 203')).toBeTruthy()
    const entraram = screen.getByRole('region', { name: 'Entrou, mas não votou (1)' })
    expect(within(entraram).getByLabelText('Bloco 1, apartamento 101')).toBeTruthy()
    const nao = screen.getByRole('region', { name: 'Ainda não entrou no Portal (2)' })
    expect(within(nao).getAllByRole('listitem')).toHaveLength(2)
    expect(document.body.textContent).not.toContain('Quinta à noite')
  })

  it('copiar a lista de quem falta', async () => {
    const escrever = vi.fn(async () => {})
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText: escrever } })
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete()),
      'GET /api/enquetes/7/votantes': json(200, {
        votaram: [],
        entraram_sem_votar: [{ login: '1101', bloco: 1, apartamento: '101' }],
        nao_entraram: [{ login: '2102', bloco: 2, apartamento: '102' }],
      }),
    })
    abrir('/enquetes/7/votantes')
    fireEvent.click(await screen.findByRole('button', { name: 'Copiar a lista de quem falta' }))
    await waitFor(() => expect(escrever).toHaveBeenCalledOnce())
    expect(escrever.mock.calls[0]).toEqual([
      'Ainda não votaram na enquete “Qual o melhor dia para a reunião?”:\n\n' +
        'Entraram no Portal, mas não votaram:\nBloco 1: 101\n\n' +
        'Ainda não entraram no Portal:\nBloco 2: 102',
    ])
  })

  it('o morador não abre a lista de quem votou', async () => {
    apiFalsa({ 'GET /api/acesso/eu': json(200, COMUM) })
    abrir('/enquetes/7/votantes')
    expect(await screen.findByRole('heading', { name: 'Sem permissão' })).toBeTruthy()
  })
})
