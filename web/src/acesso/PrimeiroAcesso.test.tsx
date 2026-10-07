// Primeiro acesso (H-01, RNF-11).
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from './apoioDeTeste'

const RESTRITA = { 'GET /api/acesso/eu': json(200, eu([], true, '1101')) }

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function preencher(campos: Record<string, string>) {
  for (const [rotulo, valor] of Object.entries(campos)) {
    fireEvent.change(screen.getByLabelText(rotulo), { target: { value: valor } })
  }
}

const BOM = {
  'Senha nova': 'casa-nova-2027',
  'Repita a senha nova': 'casa-nova-2027',
  'Nome de quem responde pela unidade': 'Socorro',
  Celular: '(81) 9 1234-5678',
}

describe('primeiro acesso', () => {
  it('mostra a placa e o aviso antes de concluir', async () => {
    apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    expect(await screen.findByRole('heading', { name: 'Primeiro acesso' })).toBeTruthy()
    expect(screen.getAllByRole('img', { name: 'Bloco 1, apartamento 101' }).length).toBe(1)
    const texto = document.querySelector('main')?.textContent ?? ''
    expect(texto).toContain('Se você não é desta unidade, não continue.')
    expect(texto).toContain('A conta é da família que mora ou vai morar aqui.')
  })

  it('pede senha duas vezes, nome, celular e e-mail marcado como opcional', async () => {
    apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    for (const rotulo of Object.keys(BOM)) expect(screen.getByLabelText(rotulo)).toBeTruthy()
    expect(screen.getByLabelText('E-mail (opcional)')).toBeTruthy()
  })

  it.each([
    ['curta', 'curta', 'A senha nova precisa ter pelo menos 8 caracteres.'],
    ['mudar123', 'mudar123', 'Escolha uma senha diferente da inicial, que todo mundo conhece.'],
  ])('recusa a senha "%s" e explica, sem chamar a API', async (senha, repetida, mensagem) => {
    const chamadas = apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    preencher({ ...BOM, 'Senha nova': senha, 'Repita a senha nova': repetida })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e entrar' }))
    expect((await screen.findByRole('alert')).textContent).toContain(mensagem)
    const campo = screen.getByLabelText('Senha nova')
    expect(campo.getAttribute('aria-invalid')).toBe('true')
    expect(document.activeElement).toBe(campo)
    expect(chamadas.some((c) => c.caminho === '/api/acesso/primeiro-acesso')).toBe(false)
  })

  it('mostra no campo certo o erro que veio da API', async () => {
    apiFalsa({
      ...RESTRITA,
      'POST /api/acesso/primeiro-acesso': json(422, {
        codigo: 'dados_invalidos',
        mensagem: 'Confira o e-mail, ou deixe em branco.',
        campos: [{ campo: 'email', mensagem: 'Confira o e-mail, ou deixe em branco.' }],
      }),
    })
    abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    preencher({ ...BOM, 'E-mail (opcional)': 'a@b.c' })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e entrar' }))
    await screen.findByRole('alert')
    await waitFor(() =>
      expect(screen.getByLabelText('E-mail (opcional)').getAttribute('aria-invalid')).toBe('true'),
    )
  })

  // M2 (H-05): na primeira vez deste aparelho, a oferta "Receber os avisos"; depois, o mural.
  it('concluído, manda os dados e cai na oferta de receber os avisos', async () => {
    const chamadas = apiFalsa({
      ...RESTRITA,
      'POST /api/acesso/primeiro-acesso': json(200, eu([], false, '1101')),
    })
    const roteador = abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    preencher(BOM)
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e entrar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/receber-avisos'))
    await screen.findByRole('heading', { name: 'Receber os avisos' })
    expect(screen.getByRole('status').textContent).toBe('Pronto! O apartamento está ativado.')
    expect(chamadas.find((c) => c.caminho === '/api/acesso/primeiro-acesso')?.corpo).toEqual({
      senha_nova: 'casa-nova-2027',
      senha_nova_repetida: 'casa-nova-2027',
      responsavel_nome: 'Socorro',
      celular: '(81) 9 1234-5678',
      email: null,
    })
  })

  it('"Não é o meu apartamento" sai da sessão e volta à entrada', async () => {
    const chamadas = apiFalsa({ ...RESTRITA, 'POST /api/acesso/sair': json(204) })
    const roteador = abrir('/primeiro-acesso')
    fireEvent.click(await screen.findByRole('button', { name: 'Não é o meu apartamento, voltar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/entrar'))
    expect(chamadas.some((c) => c.caminho === '/api/acesso/sair')).toBe(true)
  })

  it('RNF-11: a política de privacidade abre ali mesmo, antes do cadastro', async () => {
    apiFalsa(RESTRITA)
    abrir('/primeiro-acesso')
    fireEvent.click(await screen.findByText(/Ler a política de privacidade/))
    expect(screen.getByText(/O que não guardamos/)).toBeTruthy()
  })
})
