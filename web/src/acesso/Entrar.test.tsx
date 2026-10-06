// Tela de entrar (H-01, H-02, H-03, RNF-11).
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from './apoioDeTeste'

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function preencher(bloco: string, apartamento: string, senha: string) {
  fireEvent.click(screen.getByRole('radio', { name: `Bloco ${bloco}` }))
  fireEvent.change(screen.getByLabelText('Apartamento'), { target: { value: apartamento } })
  fireEvent.change(screen.getByLabelText('Senha'), { target: { value: senha } })
}

describe('tela de entrar', () => {
  it('tem o título, 5 botões de bloco, o apartamento e a senha', async () => {
    apiFalsa({})
    abrir('/entrar')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Portal Capibaribe Prime' }),
    ).toBeTruthy()
    expect(screen.getAllByRole('radio')).toHaveLength(5)
    const apartamento = screen.getByLabelText('Apartamento') as HTMLInputElement
    expect(apartamento.inputMode).toBe('numeric')
    expect((screen.getByLabelText('Senha') as HTMLInputElement).type).toBe('password')
  })

  it('apartamento aceita só números, até 3 dígitos', async () => {
    apiFalsa({})
    abrir('/entrar')
    const apartamento = (await screen.findByLabelText('Apartamento')) as HTMLInputElement
    fireEvent.change(apartamento, { target: { value: '1-0a12' } })
    expect(apartamento.value).toBe('101')
  })

  it('colar o login antigo 1203 marca o Bloco 1 e deixa 203', async () => {
    apiFalsa({})
    abrir('/entrar')
    const apartamento = (await screen.findByLabelText('Apartamento')) as HTMLInputElement
    fireEvent.paste(apartamento, { clipboardData: { getData: () => '1203' } })
    expect(apartamento.value).toBe('203')
    expect((screen.getByRole('radio', { name: 'Bloco 1' }) as HTMLInputElement).checked).toBe(true)
  })

  it('junta Bloco 1 + 7 no login 1007 e manda para a API', async () => {
    const chamadas = apiFalsa({ 'POST /api/acesso/entrar': json(200, eu([], false, '1007')) })
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '7', 'senha-certa')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() =>
      expect(chamadas.find((c) => c.caminho === '/api/acesso/entrar')?.corpo).toEqual({
        login: '1007',
        senha: 'senha-certa',
      }),
    )
  })

  it('H-02: login e senha certos abrem o mural', async () => {
    apiFalsa({ 'POST /api/acesso/entrar': json(200, eu()) })
    const roteador = abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203', 'senha-certa')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
  })

  it('H-01: com mudar123 vai direto ao primeiro acesso, não ao mural', async () => {
    apiFalsa({ 'POST /api/acesso/entrar': json(200, eu([], true, '1101')) })
    const roteador = abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '101', 'mudar123')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/primeiro-acesso'))
  })

  it('volta para a tela que a pessoa tentou abrir (link do WhatsApp)', async () => {
    apiFalsa({ 'POST /api/acesso/entrar': json(200, eu()) })
    const roteador = abrir('/minha-unidade')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203', 'senha-certa')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/minha-unidade'))
  })

  it('H-02: erro de login ou senha mostra a mesma mensagem e anuncia', async () => {
    apiFalsa({
      'POST /api/acesso/entrar': json(401, {
        codigo: 'credenciais_invalidas',
        mensagem: 'Bloco, apartamento ou senha incorretos. Confira e tente de novo.',
      }),
    })
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203', 'errada')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toContain('Bloco, apartamento ou senha incorretos.')
    // O que a pessoa escolheu e digitou fica onde estava.
    expect((screen.getByLabelText('Apartamento') as HTMLInputElement).value).toBe('203')
  })

  it('H-03: bloqueio diz quanto tempo falta e sugere falar com a administração', async () => {
    apiFalsa({
      'POST /api/acesso/entrar': json(423, {
        codigo: 'unidade_bloqueada',
        mensagem:
          'Entrada bloqueada por 12 minutos depois de várias senhas erradas. Se não foi você, avise a administração do Portal no grupo do WhatsApp.',
        bloqueada_ate: '2026-10-05T20:00:00Z',
        minutos_restantes: 12,
      }),
    })
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '101', 'mudar123')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    const alerta = await screen.findByRole('alert')
    expect(alerta.textContent).toContain('Tente de novo às 17h00.')
    expect(alerta.textContent).toContain('avise a administração do Portal')
  })

  it('sem bloco escolhido, pede o bloco sem chamar a API', async () => {
    const chamadas = apiFalsa({})
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    fireEvent.change(screen.getByLabelText('Apartamento'), { target: { value: '101' } })
    fireEvent.change(screen.getByLabelText('Senha'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Escolha o bloco')
    expect(chamadas.some((c) => c.caminho === '/api/acesso/entrar')).toBe(false)
  })

  it('apartamento que não pode existir (andar 9) dá a mesma mensagem, sem chamar a API', async () => {
    const chamadas = apiFalsa({})
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('3', '999', 'qualquer')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect((await screen.findByRole('alert')).textContent).toContain(
      'Bloco, apartamento ou senha incorretos. Confira e tente de novo.',
    )
    expect(chamadas.some((c) => c.caminho === '/api/acesso/entrar')).toBe(false)
  })

  it('sem internet, explica', async () => {
    apiFalsa({})
    vi.stubGlobal(
      'fetch',
      vi.fn(async (caminho: string) => {
        if (caminho === '/api/acesso/eu') {
          return json(401, { codigo: 'sem_sessao', mensagem: 'Entre de novo.' })
        }
        throw new TypeError('Failed to fetch')
      }),
    )
    abrir('/entrar')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203', 'x')
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Sem conexão')
  })

  it('esqueci a senha: até o M2, falar com a administração', async () => {
    apiFalsa({})
    abrir('/entrar')
    fireEvent.click(await screen.findByText('Esqueci minha senha'))
    expect(screen.getByText(/Fale com a administração do Portal no grupo do WhatsApp/)).toBeTruthy()
  })

  it('RNF-11: a política de privacidade está a um toque, antes de entrar', async () => {
    apiFalsa({})
    abrir('/entrar')
    const link = await screen.findByRole('link', { name: /política de privacidade/i })
    expect(link.getAttribute('href')).toBe('/privacidade')
  })
})
