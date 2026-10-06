// Minha unidade (H-06, RNF-12).
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { MinhaUnidade } from './tipos'
import { abrir, apiFalsa, eu, json } from './apoioDeTeste'

function dados(mudar: Partial<MinhaUnidade> = {}): MinhaUnidade {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    responsavel_nome: 'Rafael',
    celular: '81912345678',
    email: null,
    papeis: [],
    ativada_em: '2026-10-01T12:00:00Z',
    aparelhos: [
      {
        id: 7,
        descricao: 'Android · Chrome',
        criada_em: '2026-10-01T12:00:00Z',
        ultimo_uso_em: '2026-10-05T12:00:00Z',
        este_aparelho: true,
      },
      {
        id: 9,
        descricao: 'iPhone · Safari',
        criada_em: '2026-10-02T12:00:00Z',
        ultimo_uso_em: '2026-10-04T12:00:00Z',
        este_aparelho: false,
      },
    ],
    ...mudar,
  }
}

const LOGADA = { 'GET /api/acesso/eu': json(200, eu()) }

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

async function abrirMinhaUnidade(extra: Parameters<typeof apiFalsa>[0] = {}) {
  const chamadas = apiFalsa({ ...LOGADA, 'GET /api/minha-unidade': json(200, dados()), ...extra })
  const roteador = abrir('/minha-unidade')
  await screen.findByText('Rafael')
  return { chamadas, roteador }
}

describe('minha unidade · ver', () => {
  it('mostra bloco, apartamento, responsável, celular, e-mail e aparelhos', async () => {
    await abrirMinhaUnidade()
    const texto = document.querySelector('dl.ficha')?.textContent ?? ''
    expect(texto).toContain('Bloco 1, 203')
    expect(texto).toContain('(81) 9 1234-5678')
    expect(texto).toContain('não informado')
    expect(screen.getByText('Android · Chrome')).toBeTruthy()
    expect(screen.getByText('iPhone · Safari')).toBeTruthy()
    expect(screen.getByText(/^este aparelho ·/)).toBeTruthy()
  })

  it('mostra o papel de gestão', async () => {
    await abrirMinhaUnidade({
      'GET /api/minha-unidade': json(200, dados({ papeis: ['comissao'] })),
    })
    expect(screen.getByText('Comissão')).toBeTruthy()
  })
})

describe('minha unidade · editar dados', () => {
  it('abre o formulário já preenchido e salva', async () => {
    const { chamadas } = await abrirMinhaUnidade({
      'PUT /api/minha-unidade/dados': json(
        200,
        dados({ responsavel_nome: 'Rafael e Ana', email: 'casa@exemplo.com' }),
      ),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Mudar meus dados' }))
    const nome = screen.getByLabelText('Nome de quem responde pela unidade') as HTMLInputElement
    expect(nome.value).toBe('Rafael')
    fireEvent.change(nome, { target: { value: 'Rafael e Ana' } })
    fireEvent.change(screen.getByLabelText('E-mail (opcional)'), {
      target: { value: 'casa@exemplo.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dados' }))
    expect(await screen.findByText('Rafael e Ana')).toBeTruthy()
    expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({
      responsavel_nome: 'Rafael e Ana',
      celular: '(81) 9 1234-5678',
      email: 'casa@exemplo.com',
    })
    expect(screen.getByRole('status').textContent).toBe('Dados salvos.')
  })

  it('recusa nome em branco na própria tela', async () => {
    await abrirMinhaUnidade()
    fireEvent.click(screen.getByRole('button', { name: 'Mudar meus dados' }))
    fireEvent.change(screen.getByLabelText('Nome de quem responde pela unidade'), {
      target: { value: ' ' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar dados' }))
    expect((await screen.findByRole('alert')).textContent).toContain(
      'Escreva o nome de quem responde pela unidade.',
    )
  })
})

describe('minha unidade · trocar a senha', () => {
  it('pede a atual e a nova duas vezes', async () => {
    const { chamadas } = await abrirMinhaUnidade({
      'PUT /api/minha-unidade/senha': json(204),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Trocar a senha' }))
    fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: 'velha-123' } })
    fireEvent.change(screen.getByLabelText('Senha nova'), { target: { value: 'nova-12345' } })
    fireEvent.change(screen.getByLabelText('Repita a senha nova'), {
      target: { value: 'nova-12345' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar a senha nova' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.metodo === 'PUT')?.corpo).toEqual({
        senha_atual: 'velha-123',
        senha_nova: 'nova-12345',
        senha_nova_repetida: 'nova-12345',
      }),
    )
    expect(
      await screen.findByText('Senha trocada. Os outros aparelhos foram desconectados.'),
    ).toBeTruthy()
  })

  it('senha atual errada aparece no campo', async () => {
    await abrirMinhaUnidade({
      'PUT /api/minha-unidade/senha': json(400, {
        codigo: 'senha_atual_incorreta',
        mensagem: 'A senha atual não confere.',
      }),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Trocar a senha' }))
    fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: 'errada' } })
    fireEvent.change(screen.getByLabelText('Senha nova'), { target: { value: 'nova-12345' } })
    fireEvent.change(screen.getByLabelText('Repita a senha nova'), {
      target: { value: 'nova-12345' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar a senha nova' }))
    expect((await screen.findByRole('alert')).textContent).toContain('A senha atual não confere.')
    await waitFor(() =>
      expect(screen.getByLabelText('Senha atual').getAttribute('aria-invalid')).toBe('true'),
    )
  })
})

describe('minha unidade · aparelhos', () => {
  it('desconecta outro aparelho', async () => {
    let lista = dados()
    const { chamadas } = await abrirMinhaUnidade({
      'GET /api/minha-unidade': () => json(200, lista),
      'DELETE /api/minha-unidade/aparelhos/9': () => {
        lista = dados({ aparelhos: dados().aparelhos.slice(0, 1) })
        return json(204)
      },
    })
    const item = screen.getByText('iPhone · Safari').closest('.item') as HTMLElement
    fireEvent.click(within(item).getByRole('button', { name: /Desconectar/ }))
    await waitFor(() => expect(screen.queryByText('iPhone · Safari')).toBeNull())
    expect(chamadas.some((c) => c.metodo === 'DELETE')).toBe(true)
  })

  it('"Sair deste aparelho" volta à entrada', async () => {
    const { roteador } = await abrirMinhaUnidade({ 'POST /api/acesso/sair': json(204) })
    fireEvent.click(screen.getByRole('button', { name: 'Sair deste aparelho' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
  })

  it('sair sem internet avisa e continua logado', async () => {
    await abrirMinhaUnidade()
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Sair deste aparelho' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Sem conexão')
  })
})

describe('minha unidade · apagar meus dados', () => {
  it('pede confirmação antes de apagar', async () => {
    const { chamadas } = await abrirMinhaUnidade()
    fireEvent.click(screen.getByRole('button', { name: 'Apagar meus dados' }))
    expect(screen.getByRole('button', { name: 'Sim, apagar meus dados' })).toBeTruthy()
    expect(chamadas.some((c) => c.caminho === '/api/minha-unidade/apagar-dados')).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('button', { name: 'Sim, apagar meus dados' })).toBeNull()
  })

  it('confirmado, apaga e volta à entrada', async () => {
    const { chamadas, roteador } = await abrirMinhaUnidade({
      'POST /api/minha-unidade/apagar-dados': json(204),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Apagar meus dados' }))
    fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: 'minha-senha' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sim, apagar meus dados' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
    expect(chamadas.find((c) => c.caminho === '/api/minha-unidade/apagar-dados')?.corpo).toEqual({
      confirmo: true,
      senha: 'minha-senha',
    })
    expect(screen.getByRole('status').textContent).toContain('Seus dados foram apagados.')
  })

  it('com papel de gestão, mostra o motivo da recusa', async () => {
    await abrirMinhaUnidade({
      'POST /api/minha-unidade/apagar-dados': json(409, {
        codigo: 'unidade_com_papel_de_gestao',
        mensagem:
          'Este apartamento tem papel de gestão. Peça à administração do Portal para retirar o papel antes.',
      }),
    })
    fireEvent.click(screen.getByRole('button', { name: 'Apagar meus dados' }))
    fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: 'minha-senha' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sim, apagar meus dados' }))
    expect((await screen.findByRole('alert')).textContent).toContain('papel de gestão')
  })
})
