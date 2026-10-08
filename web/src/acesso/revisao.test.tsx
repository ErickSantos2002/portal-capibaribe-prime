// Revisão independente do M1, telas do épico A: C1, U2, U3, U7, U8, U11.
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { MinhaUnidade } from './tipos'
import { abrir, apiFalsa, eu, json } from './apoioDeTeste'

const rolar = vi.fn()

beforeEach(() => {
  localStorage.clear()
  // jsdom não rola nada; o teste só confere o pedido.
  Element.prototype.scrollIntoView = rolar
  rolar.mockClear()
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function dados(): MinhaUnidade {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    responsavel_nome: 'Rafael',
    celular: '81912345678',
    email: null,
    receber_avisos_email: true,
    papeis: [],
    ativada_em: '2026-10-01T12:00:00Z',
    aparelhos: [
      {
        id: 7,
        descricao: 'Android · Chrome',
        criada_em: '2026-10-01T12:00:00Z',
        ultimo_uso_em: '2026-10-05T12:00:00Z',
        este_aparelho: true,
        notificacoes: false,
      },
      {
        id: 9,
        descricao: 'Android · Chrome',
        criada_em: '2026-09-20T15:30:00Z',
        ultimo_uso_em: '2026-10-04T12:00:00Z',
        este_aparelho: false,
        notificacoes: false,
      },
    ],
  }
}

async function abrirMinhaUnidade(extra: Parameters<typeof apiFalsa>[0] = {}) {
  const chamadas = apiFalsa({
    'GET /api/acesso/eu': json(200, eu()),
    'GET /api/minha-unidade': json(200, dados()),
    ...extra,
  })
  const roteador = abrir('/minha-unidade')
  await screen.findByText('Rafael')
  return { chamadas, roteador }
}

function abrirConfirmacao() {
  fireEvent.click(screen.getByRole('button', { name: 'Apagar meus dados' }))
  return screen.getByRole('group', { name: 'Apagar os dados do apartamento?' })
}

// --- C1 ---------------------------------------------------------------------------------------

describe('C1 · apagar meus dados pede a senha atual', () => {
  it('a confirmação tem o campo de senha e o aviso em destaque', async () => {
    await abrirMinhaUnidade()
    const grupo = abrirConfirmacao()
    expect(within(grupo).getByLabelText('Senha atual')).toBeTruthy()
    const aviso = within(grupo).getByRole('note')
    expect(aviso.textContent).toContain('qualquer pessoa com a senha inicial')
    expect(aviso.textContent).toContain('avise a administração do Portal')
  })

  it('sem a senha, explica e não chama a API', async () => {
    const { chamadas } = await abrirMinhaUnidade()
    const grupo = abrirConfirmacao()
    fireEvent.click(within(grupo).getByRole('button', { name: 'Sim, apagar meus dados' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Escreva a senha atual.')
    expect(chamadas.some((c) => c.caminho === '/api/minha-unidade/apagar-dados')).toBe(false)
  })

  it('manda a senha junto da confirmação', async () => {
    const { chamadas, roteador } = await abrirMinhaUnidade({
      'POST /api/minha-unidade/apagar-dados': json(204),
    })
    const grupo = abrirConfirmacao()
    fireEvent.change(within(grupo).getByLabelText('Senha atual'), {
      target: { value: 'minha-senha' },
    })
    fireEvent.click(within(grupo).getByRole('button', { name: 'Sim, apagar meus dados' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
    expect(chamadas.find((c) => c.caminho === '/api/minha-unidade/apagar-dados')?.corpo).toEqual({
      confirmo: true,
      senha: 'minha-senha',
    })
  })

  it('senha errada aparece no campo', async () => {
    await abrirMinhaUnidade({
      'POST /api/minha-unidade/apagar-dados': json(400, {
        codigo: 'senha_atual_incorreta',
        mensagem: 'A senha atual não confere.',
        campos: [{ campo: 'senha', mensagem: 'A senha atual não confere.' }],
        tentativas_restantes: 4,
      }),
    })
    const grupo = abrirConfirmacao()
    const campo = within(grupo).getByLabelText('Senha atual')
    fireEvent.change(campo, { target: { value: 'errada' } })
    fireEvent.click(within(grupo).getByRole('button', { name: 'Sim, apagar meus dados' }))
    expect((await screen.findByRole('alert')).textContent).toContain('A senha atual não confere.')
    await waitFor(() => expect(campo.getAttribute('aria-invalid')).toBe('true'))
  })
})

// --- U2 ---------------------------------------------------------------------------------------

describe('U2 · confirmação no meio da tela', () => {
  it('rola o bloco de confirmação inteiro para o centro', async () => {
    await abrirMinhaUnidade()
    const grupo = abrirConfirmacao()
    await waitFor(() => expect(rolar).toHaveBeenCalled())
    expect(rolar.mock.contexts.at(-1)).toBe(grupo)
    expect(rolar.mock.calls.at(-1)?.[0]).toMatchObject({ block: 'center' })
  })
})

// --- U3 ---------------------------------------------------------------------------------------

describe('U3 · entrar', () => {
  function preencher() {
    fireEvent.click(screen.getByRole('radio', { name: 'Bloco 1' }))
    fireEvent.change(screen.getByLabelText('Apartamento'), {
      target: { value: '101' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'x' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
  }

  it('no bloqueio, diz o horário de Recife para tentar de novo', async () => {
    apiFalsa({
      'POST /api/acesso/entrar': json(423, {
        codigo: 'unidade_bloqueada',
        mensagem: 'Entrada bloqueada por 12 minutos depois de várias senhas erradas.',
        bloqueada_ate: '2026-10-05T20:07:00Z',
        minutos_restantes: 12,
      }),
    })
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher()
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toContain('Tente de novo às 17h07.')
    expect(alerta.textContent).toContain('avise a administração do Portal')
  })

  it('mostra quantas tentativas faltam (mensagem da API)', async () => {
    apiFalsa({
      'POST /api/acesso/entrar': json(401, {
        codigo: 'credenciais_invalidas',
        mensagem:
          'Bloco, apartamento ou senha incorretos. Confira e tente de novo. Faltam 2 tentativas antes de a entrada ser bloqueada por 15 minutos.',
        tentativas_restantes: 2,
      }),
    })
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher()
    expect((await screen.findByRole('alert')).textContent).toContain('Faltam 2 tentativas')
  })

  it('botão de mostrar e ocultar a senha', async () => {
    apiFalsa({})
    abrir('/entrar')
    const senha = (await screen.findByLabelText('Senha')) as HTMLInputElement
    const botao = screen.getByRole('button', { name: 'Mostrar senha' })
    expect(botao.getAttribute('aria-controls')).toBe(senha.id)
    fireEvent.click(botao)
    expect(senha.type).toBe('text')
    fireEvent.click(screen.getByRole('button', { name: 'Ocultar senha' }))
    expect(senha.type).toBe('password')
  })

  it('todo campo de senha do app tem o botão', async () => {
    await abrirMinhaUnidade()
    fireEvent.click(screen.getByRole('button', { name: 'Trocar a senha' }))
    for (const rotulo of ['Senha atual', 'Senha nova', 'Repita a senha nova']) {
      expect(screen.getByRole('button', { name: `Mostrar ${rotulo.toLowerCase()}` })).toBeTruthy()
    }
  })
})

// --- U7 ---------------------------------------------------------------------------------------

describe('U7 · trocar a senha', () => {
  function preencher(atual: string, nova: string) {
    fireEvent.click(screen.getByRole('button', { name: 'Trocar a senha' }))
    fireEvent.change(screen.getByLabelText('Senha atual'), {
      target: { value: atual },
    })
    fireEvent.change(screen.getByLabelText('Senha nova'), {
      target: { value: nova },
    })
    fireEvent.change(screen.getByLabelText('Repita a senha nova'), {
      target: { value: nova },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar a senha nova' }))
  }

  it('recusa a nova igual à atual sem chamar a API', async () => {
    const { chamadas } = await abrirMinhaUnidade()
    preencher('mesma-senha-1', 'mesma-senha-1')
    expect((await screen.findByRole('alert')).textContent).toContain(
      'A senha nova é igual à atual. Escolha uma diferente.',
    )
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(false)
  })

  it('depois de salvar, o foco vai para o recado de sucesso', async () => {
    await abrirMinhaUnidade({ 'PUT /api/minha-unidade/senha': json(204) })
    preencher('velha-123', 'nova-12345')
    await waitFor(() =>
      expect(document.activeElement?.textContent).toContain(
        'Senha trocada. Os outros aparelhos foram desconectados.',
      ),
    )
  })
})

// --- U8 ---------------------------------------------------------------------------------------

describe('U8 · primeiro acesso', () => {
  const RESTRITA = { 'GET /api/acesso/eu': json(200, eu([], true, '1101')) }

  it('a dica diz a regra real da senha', async () => {
    apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    const ajuda = document.getElementById('pa-senha_nova-ajuda')?.textContent ?? ''
    expect(ajuda).toContain('Pelo menos 8 caracteres')
    expect(ajuda).toContain('espaços')
    expect(ajuda).toContain('símbolos')
  })

  it('"Ler a política" vem antes de "Salvar e entrar"', async () => {
    apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    const politica = screen.getByText(/Ler a política de privacidade/)
    const salvar = screen.getByRole('button', { name: 'Salvar e entrar' })
    expect(politica.compareDocumentPosition(salvar) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})

// --- U11 --------------------------------------------------------------------------------------

describe('U11 · aparelhos de mesmo nome', () => {
  it('mostram quando entraram e o último uso', async () => {
    await abrirMinhaUnidade()
    const itens = document.querySelectorAll('.acesso-aparelho')
    expect(itens).toHaveLength(2)
    expect(itens[0].textContent).toContain('entrou em 1 de out., 09:00')
    expect(itens[1].textContent).toContain('entrou em 20 de set., 12:30')
    expect(itens[1].textContent).toContain('último uso em 4 de out., 09:00')
  })
})
