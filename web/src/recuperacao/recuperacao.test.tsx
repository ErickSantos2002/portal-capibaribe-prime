// Esqueci a senha (H-04; spec do épico B do M2, seção 3): o link na entrada, o pedido e a tela
// do link do e-mail, com o Portal inteiro montado (mesmas rotas e guardas de produção).
import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'

const MSG_PEDIDO =
  'Se houver e-mail cadastrado, enviamos um link. Se não chegou, fale com a administração.'
const MSG_INVALIDO = 'Este link venceu ou já foi usado. Peça outro em "Esqueci minha senha".'
const UNIDADE = { login: '1203', bloco: 1, apartamento: '203' }
const ASSUNTO = 'Portal Capibaribe Prime: criar senha nova'
const PEDIDA = { mensagem: MSG_PEDIDO, remetente: 'capibaribeprime@example.com', assunto: ASSUNTO }

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('na tela de entrar', () => {
  it('"Esqueci minha senha" é um link para a tela de pedir o link', async () => {
    apiFalsa({})
    abrir('/entrar')
    const link = await screen.findByRole('link', { name: 'Esqueci minha senha' })
    expect(link.getAttribute('href')).toBe('/esqueci-a-senha')
  })
})

describe('esqueci minha senha', () => {
  function preencher(bloco: string, apartamento: string) {
    fireEvent.click(screen.getByRole('radio', { name: `Bloco ${bloco}` }))
    fireEvent.change(screen.getByLabelText('Apartamento'), { target: { value: apartamento } })
  }

  it('pede só bloco e apartamento e manda o login montado', async () => {
    const chamadas = apiFalsa({
      'POST /api/acesso/recuperacao': json(202, PEDIDA),
    })
    abrir('/esqueci-a-senha')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Esqueci minha senha' }),
    ).toBeTruthy()
    expect(screen.getAllByRole('radio')).toHaveLength(5)
    expect(screen.queryByLabelText('Senha')).toBeNull()
    preencher('1', '203')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    // Numa região de status: o leitor de tela anuncia.
    expect((await screen.findByText(MSG_PEDIDO)).closest('[role="status"]')).toBeTruthy()
    expect(chamadas.find((c) => c.caminho === '/api/acesso/recuperacao')?.corpo).toEqual({
      login: '1203',
    })
    // A caixa recebe o foco: o leitor de tela lê o resultado logo.
    const caixa = screen.getByText(MSG_PEDIDO).closest('[role="status"]')
    await waitFor(() => expect(document.activeElement).toBe(caixa))
    // Onde procurar o e-mail: para quem, de quem, com que assunto, e o Spam.
    const detalhe = screen.getByText(/Pedido feito para o/).textContent ?? ''
    expect(detalhe.replace(/\s+/g, ' ')).toBe(
      'Pedido feito para o Bloco 1, apartamento 203. O e-mail chega em alguns minutos, de ' +
        'Portal Capibaribe Prime (capibaribeprime@example.com), com o assunto ' +
        `“${ASSUNTO}”. Se não aparecer, olhe também em Spam ou Lixo eletrônico. ` +
        'O link vale por 1 hora.',
    )
    // Quem não tem e-mail sabe o que fazer, sem a tela revelar se a unidade tem.
    expect(
      screen.getByText(
        /Sem e-mail cadastrado, fale com a administração do Portal no grupo do WhatsApp\. Ela volta a senha do apartamento para a senha que a Comissão mandou no grupo\./,
      ),
    ).toBeTruthy()
    expect(
      screen.getByRole('link', { name: 'Voltar para a entrada' }).getAttribute('href'),
    ).toBe('/entrar')
  })

  it('a mensagem depois de pedir é a da API, a mesma para qualquer apartamento', async () => {
    apiFalsa({ 'POST /api/acesso/recuperacao': json(202, PEDIDA) })
    abrir('/esqueci-a-senha')
    await screen.findByLabelText('Apartamento')
    preencher('5', '708')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    expect(await screen.findByText(MSG_PEDIDO)).toBeTruthy()
  })

  it('sem o endereço do Portal na configuração, a frase não mostra endereço', async () => {
    apiFalsa({ 'POST /api/acesso/recuperacao': json(202, { ...PEDIDA, remetente: null }) })
    abrir('/esqueci-a-senha')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    const detalhe = (await screen.findByText(/Pedido feito para o/)).textContent ?? ''
    expect(detalhe).toContain('de Portal Capibaribe Prime, com o assunto')
    expect(detalhe).not.toContain('(')
  })

  it.each([
    ['', '203', 'Escolha o bloco nos botões de 1 a 5.'],
    ['1', '', 'Escreva o número do apartamento, como 101.'],
    ['1', '901', 'Esse apartamento não existe. Confira o bloco e o número da porta.'],
    // A planta do prédio (protótipo): andares 0 a 7, apartamentos 01 a 08.
    ['1', '199', 'Esse apartamento não existe. Confira o bloco e o número da porta.'],
    ['1', '110', 'Esse apartamento não existe. Confira o bloco e o número da porta.'],
    ['1', '820', 'Esse apartamento não existe. Confira o bloco e o número da porta.'],
  ])('bloco %j e apartamento %j: avisa antes de mandar', async (bloco, apartamento, erro) => {
    const chamadas = apiFalsa({})
    abrir('/esqueci-a-senha')
    await screen.findByLabelText('Apartamento')
    if (bloco) fireEvent.click(screen.getByRole('radio', { name: `Bloco ${bloco}` }))
    fireEvent.change(screen.getByLabelText('Apartamento'), { target: { value: apartamento } })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    expect((await screen.findByRole('alert')).textContent).toContain(erro)
    expect(chamadas.some((c) => c.caminho === '/api/acesso/recuperacao')).toBe(false)
  })

  it('colar o login antigo 1203 marca o Bloco 1', async () => {
    apiFalsa({})
    abrir('/esqueci-a-senha')
    const apartamento = (await screen.findByLabelText('Apartamento')) as HTMLInputElement
    fireEvent.paste(apartamento, { clipboardData: { getData: () => '1203' } })
    expect(apartamento.value).toBe('203')
    expect((screen.getByRole('radio', { name: 'Bloco 1' }) as HTMLInputElement).checked).toBe(true)
  })

  it('sem internet: diz o que houve e deixa tentar de novo', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (caminho: string) => {
        if (caminho === '/api/acesso/eu') return json(401, { codigo: 'sem_sessao', mensagem: 'x' })
        throw new TypeError('Failed to fetch')
      }),
    )
    abrir('/esqueci-a-senha')
    await screen.findByLabelText('Apartamento')
    preencher('1', '203')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar link' }))
    expect((await screen.findByRole('alert')).textContent).toContain('Sem conexão')
    expect(screen.getByRole('button', { name: 'Enviar link' })).toBeTruthy()
  })

  it('quem já está entrado vai para o mural', async () => {
    apiFalsa({ 'GET /api/acesso/eu': json(200, eu()) })
    const roteador = abrir('/esqueci-a-senha')
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
  })
})

describe('criar senha nova pelo link do e-mail', () => {
  function senhas(senha: string, repetida = senha) {
    fireEvent.change(screen.getByLabelText('Senha nova'), { target: { value: senha } })
    fireEvent.change(screen.getByLabelText('Repita a senha nova'), {
      target: { value: repetida },
    })
  }

  it('confere o link, tira o token da barra e mostra a placa', async () => {
    const chamadas = apiFalsa({
      'POST /api/acesso/recuperacao/conferir': json(200, { unidade: UNIDADE }),
    })
    const roteador = abrir('/redefinir-senha#token=segredo-do-link')
    expect(await screen.findByText(/Bloco 1, apartamento 203/)).toBeTruthy()
    expect(
      chamadas.find((c) => c.caminho === '/api/acesso/recuperacao/conferir')?.corpo,
    ).toEqual({ token: 'segredo-do-link' })
    expect(roteador.state.location.hash).toBe('')
  })

  it('salva a senha nova, entra e avisa que os outros aparelhos saíram', async () => {
    const chamadas = apiFalsa({
      'POST /api/acesso/recuperacao/conferir': json(200, { unidade: UNIDADE }),
      'POST /api/acesso/recuperacao/redefinir': json(200, eu()),
      'GET /api/avisos': json(200, { itens: [], proxima: null }),
    })
    const roteador = abrir('/redefinir-senha#token=segredo-do-link')
    await screen.findByLabelText('Senha nova')
    senhas('senha nova boa')
    fireEvent.click(screen.getByRole('button', { name: 'Salvar senha nova' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/avisos'))
    expect(
      chamadas.find((c) => c.caminho === '/api/acesso/recuperacao/redefinir')?.corpo,
    ).toEqual({
      token: 'segredo-do-link',
      senha_nova: 'senha nova boa',
      senha_nova_repetida: 'senha nova boa',
    })
    expect(
      await screen.findByText(
        'Senha nova criada. Os outros aparelhos foram desconectados. Avise a família da senha nova.',
      ),
    ).toBeTruthy()
  })

  it.each([
    ['curta', 'curta', 'A senha nova precisa ter pelo menos 8 caracteres.'],
    ['mudar123', 'mudar123', 'Escolha uma senha diferente da inicial, que todo mundo conhece.'],
    ['senha boa 1', 'senha boa 2', 'As duas senhas estão diferentes. Escreva a mesma nas duas.'],
  ])('as regras de senha do primeiro acesso: %j', async (senha, repetida, erro) => {
    const chamadas = apiFalsa({
      'POST /api/acesso/recuperacao/conferir': json(200, { unidade: UNIDADE }),
    })
    abrir('/redefinir-senha#token=t')
    await screen.findByLabelText('Senha nova')
    senhas(senha, repetida)
    fireEvent.click(screen.getByRole('button', { name: 'Salvar senha nova' }))
    expect((await screen.findByRole('alert')).textContent).toContain(erro)
    expect(chamadas.some((c) => c.caminho === '/api/acesso/recuperacao/redefinir')).toBe(false)
  })

  it('link vencido ou usado: diz o que houve e leva a pedir outro', async () => {
    apiFalsa({
      'POST /api/acesso/recuperacao/conferir': json(410, {
        codigo: 'link_invalido',
        mensagem: MSG_INVALIDO,
      }),
    })
    abrir('/redefinir-senha#token=velho')
    expect(await screen.findByText(MSG_INVALIDO)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Pedir outro link' }).getAttribute('href')).toBe(
      '/esqueci-a-senha',
    )
    expect(screen.queryByLabelText('Senha nova')).toBeNull()
  })

  it('link já usado com o aparelho entrado: leva aos avisos, não a pedir outro link', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'POST /api/acesso/recuperacao/conferir': json(410, {
        codigo: 'link_invalido',
        mensagem: MSG_INVALIDO,
      }),
    })
    abrir('/redefinir-senha#token=usado')
    expect(
      await screen.findByText(
        'Você já está no Portal. Para trocar a senha de novo, vá em Minha unidade.',
      ),
    ).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ir para os avisos' }).getAttribute('href')).toBe(
      '/avisos',
    )
    expect(screen.queryByRole('link', { name: 'Pedir outro link' })).toBeNull()
  })

  it('sem token no endereço: a mesma tela, sem chamar a API', async () => {
    const chamadas = apiFalsa({})
    abrir('/redefinir-senha')
    expect(await screen.findByRole('link', { name: 'Pedir outro link' })).toBeTruthy()
    expect(chamadas.some((c) => c.caminho.startsWith('/api/acesso/recuperacao'))).toBe(false)
  })

  it('o link vence enquanto a pessoa digita: ao salvar, a tela de link vencido', async () => {
    apiFalsa({
      'POST /api/acesso/recuperacao/conferir': json(200, { unidade: UNIDADE }),
      'POST /api/acesso/recuperacao/redefinir': json(410, {
        codigo: 'link_invalido',
        mensagem: MSG_INVALIDO,
      }),
    })
    abrir('/redefinir-senha#token=t')
    await screen.findByLabelText('Senha nova')
    senhas('senha nova boa')
    fireEvent.click(screen.getByRole('button', { name: 'Salvar senha nova' }))
    expect(await screen.findByText(MSG_INVALIDO)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Pedir outro link' })).toBeTruthy()
  })

  it('sem internet ao conferir: deixa tentar de novo', async () => {
    let vez = 0
    apiFalsa({
      'POST /api/acesso/recuperacao/conferir': () => {
        vez += 1
        if (vez === 1) throw new TypeError('Failed to fetch')
        return json(200, { unidade: UNIDADE })
      },
    })
    abrir('/redefinir-senha#token=t')
    fireEvent.click(await screen.findByRole('button', { name: 'Tentar de novo' }))
    expect(await screen.findByLabelText('Senha nova')).toBeTruthy()
  })
})
