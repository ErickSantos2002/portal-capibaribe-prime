// M4 · ajustes das revisões finais (costura entre os épicos e usabilidade), na tela de votar, na
// lista, na de votantes e no cartão do aviso. Cada teste falhava antes da correção.
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createElement } from 'react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../../acesso/apoioDeTeste'
import type { Enquete, EnqueteResumo, Votantes } from '../tipos'
import { EnqueteDoAviso } from './EnqueteDoAviso'
import { faltamParaCopiar, participacaoEmTexto, porcentagemEmTexto } from './formatos'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const FIM = '2099-11-10T23:00:00Z'
const FIM_TEXTO = '10 de novembro de 2099, às 20h'
const COMUM = eu()
const COMISSAO = eu(['comissao'], false, '2304')

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
    ...resumo(7, { pergunta: 'Qual o melhor dia?' }),
    opcoes: [
      { id: 21, texto: 'Terça', votos: 0 },
      { id: 22, texto: 'Quinta', votos: 0 },
    ],
    meu_voto: [],
    votado_em: null,
    participacao: { votaram: 0, total: 320 },
    resultado_visivel: true,
    pode_votar: true,
    pode_editar: false,
    aviso_id: 40,
    ...extra,
  }
}

function voltarParaATela() {
  Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
  document.dispatchEvent(new Event('visibilitychange'))
}

// --- costura -----------------------------------------------------------------------------------

describe('costura entre editar e votar', () => {
  it('1: um 422 do voto também recarrega a enquete', async () => {
    let leituras = 0
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': () => {
        leituras++
        return json(200, enquete({ multipla_escolha: leituras === 1 }))
      },
      'PUT /api/enquetes/7/voto': json(422, {
        codigo: 'dados_invalidos',
        mensagem: 'Nesta enquete, escolha só uma opção.',
        campos: [{ campo: 'opcoes', mensagem: 'Nesta enquete, escolha só uma opção.' }],
      }),
    })
    abrir('/enquetes/7')
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Terça' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Quinta' }))
    fireEvent.click(screen.getByRole('button', { name: 'Votar' }))
    expect(await screen.findByRole('radio', { name: 'Terça' })).toBeTruthy()
    expect(leituras).toBe(2)
    expect(screen.getByRole('alert').textContent).toContain('Nesta enquete, escolha só uma opção.')
  })

  it('2: a escolha velha não sobrevive às opções recriadas; o botão fica desligado e diz por quê', async () => {
    let leitura = 0
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': () =>
        json(
          200,
          leitura++ === 0
            ? enquete()
            : enquete({
                pergunta: 'Qual o melhor dia? (corrigida)',
                editada_em: '2026-11-02T12:00:00Z',
                opcoes: [
                  { id: 31, texto: 'Terça', votos: 0 },
                  { id: 32, texto: 'Quinta', votos: 0 },
                ],
              }),
        ),
    })
    abrir('/enquetes/7')
    fireEvent.click(await screen.findByRole('radio', { name: 'Terça' }))
    voltarParaATela()
    await screen.findByRole('heading', { name: 'Qual o melhor dia? (corrigida)' })
    const botao = screen.getByRole('button', { name: 'Votar' }) as HTMLButtonElement
    expect(botao.disabled).toBe(true)
    expect(screen.getByText('Escolha uma opção para votar.')).toBeTruthy()
  })

  it('2: sem a escolha velha, volta ao voto gravado', async () => {
    let leitura = 0
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': () =>
        json(
          200,
          leitura++ === 0
            ? enquete()
            : enquete({
                // Outra pessoa da casa votou na 22; a 21 deixou de existir nesta leitura.
                opcoes: [
                  { id: 22, texto: 'Quinta', votos: 1 },
                  { id: 23, texto: 'Sábado', votos: 0 },
                ],
                meu_voto: [22],
                ja_votou: true,
              }),
        ),
    })
    abrir('/enquetes/7')
    fireEvent.click(await screen.findByRole('radio', { name: 'Terça' }))
    voltarParaATela()
    const quinta = (await screen.findByRole('radio', { name: 'Sábado' }), screen.getByRole('radio', { name: 'Quinta' })) as HTMLInputElement
    expect(quinta.checked).toBe(true)
    expect((screen.getByRole('button', { name: 'Trocar voto' }) as HTMLButtonElement).disabled).toBe(true)
  })
})

// --- telas -------------------------------------------------------------------------------------

describe('votar', () => {
  it('6: escolha diferente do voto gravado avisa que ainda não trocou', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete({ meu_voto: [21], ja_votou: true })),
    })
    abrir('/enquetes/7')
    const quinta = await screen.findByRole('radio', { name: 'Quinta' })
    const aviso = () => document.querySelector('.enq-pendente') as HTMLElement
    expect(aviso().getAttribute('aria-live')).toBe('polite')
    expect(aviso().textContent).toBe('')
    fireEvent.click(quinta)
    expect(aviso().textContent).toBe('Você ainda não trocou o voto. Toque em Trocar voto para valer.')
    expect(within(aviso()).getByText('Trocar voto').tagName).toBe('B')
    fireEvent.click(screen.getByRole('radio', { name: 'Terça' }))
    expect(aviso().textContent).toBe('')
  })

  it('15: depois de votar, a legenda convida a trocar (única e múltipla)', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete({ meu_voto: [21], ja_votou: true })),
    })
    abrir('/enquetes/7')
    expect(await screen.findByRole('group', { name: 'Quer trocar? Escolha outra opção.' })).toBeTruthy()
    expect(screen.queryByText('Escolha uma opção.')).toBeNull()
    cleanup()
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({ multipla_escolha: true, meu_voto: [21], ja_votou: true }),
      ),
    })
    abrir('/enquetes/7')
    expect(
      await screen.findByRole('group', {
        name: 'Quer trocar? Marque ou desmarque e toque em Trocar voto.',
      }),
    ).toBeTruthy()
  })

  it('15: antes de votar, a legenda continua pedindo a escolha', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
    })
    abrir('/enquetes/7')
    expect(await screen.findByRole('group', { name: 'Escolha uma opção.' })).toBeTruthy()
  })

  it('20: a gestão fora do destino também vê até quando vai', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ para_todos: false, blocos: [1], pode_votar: false })),
    })
    abrir('/enquetes/7')
    expect(await screen.findByText(`Vai até ${FIM_TEXTO}.`)).toBeTruthy()
  })
})

describe('resultado', () => {
  it('13: na múltipla, uma linha explica a soma acima de 100%', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({
          multipla_escolha: true,
          opcoes: [
            { id: 21, texto: 'Terça', votos: 3 },
            { id: 22, texto: 'Quinta', votos: 2 },
          ],
          participacao: { votaram: 3, total: 10 },
        }),
      ),
    })
    abrir('/enquetes/7')
    const resultado = await screen.findByRole('region', { name: 'Como está até agora' })
    expect(resultado.textContent).toContain(
      'Cada apartamento pode marcar mais de uma opção, então a soma das porcentagens pode passar de 100%.',
    )
    cleanup()
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(200, enquete()),
    })
    abrir('/enquetes/7')
    const unica = await screen.findByRole('region', { name: 'Como está até agora' })
    expect(unica.textContent).not.toContain('passar de 100%')
  })

  it('14: abaixo de 1% vira "menos de 1%"', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({
          opcoes: [
            { id: 21, texto: 'Terça', votos: 1 },
            { id: 22, texto: 'Quinta', votos: 299 },
          ],
          participacao: { votaram: 300, total: 320 },
        }),
      ),
    })
    abrir('/enquetes/7')
    const resultado = await screen.findByRole('region', { name: 'Como está até agora' })
    expect(within(resultado).getByText('1 voto, menos de 1%')).toBeTruthy()
    expect(
      within(resultado).getByRole('meter', { name: 'Terça' }).getAttribute('aria-valuetext'),
    ).toBe('menos de 1%')
  })

  it('17: terminada, a mais votada tem o selo de texto (no empate, todas)', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({
          encerrada: true,
          pode_votar: false,
          opcoes: [
            { id: 21, texto: 'Terça', votos: 5 },
            { id: 22, texto: 'Quinta', votos: 5 },
            { id: 23, texto: 'Sábado', votos: 2 },
          ],
          participacao: { votaram: 12, total: 320 },
        }),
      ),
    })
    abrir('/enquetes/7')
    const resultado = await screen.findByRole('region', { name: 'Resultado' })
    expect(within(resultado).getAllByText('Mais votada')).toHaveLength(2)
    const sabado = within(resultado).getByText('Sábado').closest('li') as HTMLElement
    expect(sabado.textContent).not.toContain('Mais votada')
  })

  it('17: aberta, ninguém ganha o selo', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes/7': json(
        200,
        enquete({ opcoes: [{ id: 21, texto: 'Terça', votos: 5 }, { id: 22, texto: 'Quinta', votos: 1 }], participacao: { votaram: 6, total: 320 } }),
      ),
    })
    abrir('/enquetes/7')
    await screen.findByRole('region', { name: 'Como está até agora' })
    expect(screen.queryByText('Mais votada')).toBeNull()
  })
})

describe('sigilo', () => {
  it('12: a promessa é honesta sobre a unanimidade', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(200, enquete({ mostrar_resultado: 'so_no_fim', resultado_visivel: false })),
    })
    abrir('/enquetes/7')
    const cartao = await screen.findByRole('link', { name: /Quais apartamentos votaram/ })
    expect(cartao.textContent).not.toContain('Sem mostrar o voto de ninguém')
    expect(cartao.textContent).toContain('Mostra quem votou, não em quê')
  })
})

describe('formatos', () => {
  it('14: porcentagem em texto', () => {
    expect(porcentagemEmTexto(1, 320)).toBe('menos de 1%')
    expect(porcentagemEmTexto(0, 320)).toBe('0%')
    expect(porcentagemEmTexto(2, 320)).toBe('1%')
    expect(porcentagemEmTexto(88, 192)).toBe('46%')
    expect(porcentagemEmTexto(0, 0)).toBe('0%')
    expect(participacaoEmTexto({ votaram: 1, total: 320 })).toBe(
      '1 de 320 apartamentos votou (menos de 1%).',
    )
  })

  it('18: o texto copiado vem em ordem crescente, por bloco e apartamento', () => {
    const lista: Votantes = {
      votaram: [],
      entraram_sem_votar: [
        { login: '2701', bloco: 2, apartamento: '701' },
        { login: '1105', bloco: 1, apartamento: '105' },
        { login: '1003', bloco: 1, apartamento: '003' },
        { login: '1702', bloco: 1, apartamento: '702' },
      ],
      nao_entraram: [],
    }
    expect(faltamParaCopiar('P?', lista)).toBe(
      'Ainda não votaram na enquete “P?”:\n\n' +
        'Entraram no Portal, mas não votaram:\nBloco 1: 003, 105, 702\nBloco 2: 701',
    )
  })
})

describe('votantes', () => {
  const lista: Votantes = {
    votaram: [{ login: '1203', bloco: 1, apartamento: '203' }],
    entraram_sem_votar: [],
    nao_entraram: [
      { login: '1701', bloco: 1, apartamento: '701' },
      { login: '1102', bloco: 1, apartamento: '102' },
      { login: '1001', bloco: 1, apartamento: '001' },
      { login: '1101', bloco: 1, apartamento: '101' },
    ],
  }

  async function abrirVotantes() {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMISSAO),
      'GET /api/enquetes/7': json(
        200,
        enquete({ mostrar_resultado: 'so_no_fim', resultado_visivel: false, participacao: { votaram: 1, total: 320 } }),
      ),
      'GET /api/enquetes/7/votantes': json(200, lista),
    })
    abrir('/enquetes/7/votantes')
    return screen.findByRole('region', { name: 'Ainda não entrou no Portal (4)' })
  }

  it('18: em ordem crescente na tela, e o andar novo começa a linha', async () => {
    const grupo = await abrirVotantes()
    const itens = within(grupo).getAllByRole('listitem')
    expect(itens.map((i) => i.textContent)).toEqual(['001', '101', '102', '701'])
    expect(itens.map((i) => i.classList.contains('enq-andar-novo'))).toEqual([
      true,
      true,
      false,
      true,
    ])
  })

  it('14 e 12: "menos de 1%" e a frase honesta do sigilo', async () => {
    await abrirVotantes()
    expect(screen.getByText('1 de 320 apartamentos votou (menos de 1%).')).toBeTruthy()
    expect(document.body.textContent).not.toContain('nunca em quê')
    expect(document.body.textContent).toContain('quando todos escolhem a mesma opção')
  })
})

describe('lista', () => {
  it('19: "ainda não votou" usa a cor de atenção, não o verde', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/enquetes': json(200, { itens: [resumo(1)] }),
    })
    abrir('/enquetes')
    const selo = await screen.findByText('Seu apartamento ainda não votou')
    expect(selo.classList.contains('enq-falta')).toBe(true)
    expect(selo.classList.contains('novo')).toBe(false)
  })
})

describe('cartão do aviso', () => {
  function cartao(encerrada: boolean) {
    render(
      createElement(
        MemoryRouter,
        null,
        createElement(EnqueteDoAviso, {
          enquete: { id: 3, pergunta: 'Qual o melhor dia?', encerra_em: FIM, encerrada },
        }),
      ),
    )
    return screen.getByRole('link', { name: /Ir para a enquete/ })
  }

  it('11: aberta diz até quando vai', () => {
    expect(cartao(false).textContent).toContain(`Aberta · vai até ${FIM_TEXTO}`)
  })

  it('11: terminada diz que terminou', () => {
    const link = cartao(true)
    expect(link.textContent).toContain('Terminou · ver o resultado')
    expect(link.textContent).not.toContain('Aberta')
  })

  it('10: no aviso aberto, o cartão vem antes do texto', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, COMUM),
      'GET /api/avisos/40': json(200, {
        id: 40,
        titulo: 'Enquete nova: Qual o melhor dia?',
        resumo: 'Uma enquete nova está aberta no Portal.',
        categoria: 'geral',
        fixado: false,
        para_todos: true,
        blocos: [],
        publicado_em: '2026-10-14T12:00:00Z',
        publicado_por: 'Comissão',
        editado_em: null,
        arquivado_em: null,
        lido: true,
        corrigido_desde_a_leitura: false,
        evento_quando: null,
        quantidade_anexos: 0,
        texto: 'Uma enquete nova está aberta no Portal.',
        evento: null,
        versoes_anteriores: [],
        leitura: null,
        anexos: [],
        documento: null,
        enquete: { id: 7, pergunta: 'Qual o melhor dia?', encerra_em: FIM, encerrada: false },
      }),
      'PUT /api/avisos/40/leitura': json(204),
    })
    abrir('/avisos/40')
    const link = await screen.findByRole('link', { name: /Ir para a enquete/ })
    const texto = screen.getByText('Uma enquete nova está aberta no Portal.')
    expect(link.compareDocumentPosition(texto) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    await waitFor(() => expect(link.isConnected).toBe(true))
  })
})
