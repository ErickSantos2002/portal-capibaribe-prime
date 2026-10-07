// Épico A do M2 · telas: "Receber os avisos" (oferta única depois do primeiro acesso) e a seção
// "Notificações" de Minha unidade (H-05; spec m2-push.md, seções 3.2 e 3.3).
import { cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import type { MinhaUnidade } from '../acesso/tipos'
import { aparelhoFalso, CHAVE, inscricaoFalsa, UA } from './apoioDeTeste'
import { ouvirPedidoDeInstalacao } from './aparelho'
import { CHAVE_OFERTA } from './ganchos'
import { CHAVE_DONO } from './inscricao'
import { CHAVE_FAIXA } from './FaixaNotificacoes'

const LOGADA = { 'GET /api/acesso/eu': json(200, eu()) }
const LIGADO = (este_aparelho = false) =>
  json(200, { disponivel: true, chave_publica: CHAVE, este_aparelho })
const DESLIGADO = json(200, { disponivel: false, chave_publica: null, este_aparelho: false })

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

async function abrirOferta(estado: Response = LIGADO(), extra: Parameters<typeof apiFalsa>[0] = {}) {
  const chamadas = apiFalsa({ ...LOGADA, 'GET /api/notificacoes': estado, ...extra })
  const roteador = abrir('/receber-avisos')
  await screen.findByRole('heading', { name: 'Quer ser avisado na hora?' })
  return { chamadas, roteador }
}

const cartao = (titulo: string) =>
  screen.getByRole('heading', { name: titulo }).closest('section') as HTMLElement

describe('Receber os avisos', () => {
  it('o primeiro acesso leva para cá uma vez, dizendo que ativou', async () => {
    aparelhoFalso()
    const restrita = json(200, eu([], true))
    apiFalsa({
      'GET /api/acesso/eu': restrita,
      'POST /api/acesso/primeiro-acesso': json(200, eu()),
      'GET /api/notificacoes': LIGADO(),
    })
    const roteador = abrir('/primeiro-acesso')
    await screen.findByRole('heading', { name: 'Primeiro acesso' })
    for (const [rotulo, valor] of [
      ['Senha nova', 'casa-nova-2027'],
      ['Repita a senha nova', 'casa-nova-2027'],
      ['Nome de quem responde', 'Socorro'],
      ['Celular', '81912345678'],
    ]) {
      fireEvent.change(screen.getByLabelText(new RegExp(`^${rotulo}`)), { target: { value: valor } })
    }
    fireEvent.click(screen.getByRole('button', { name: 'Salvar e entrar' }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/receber-avisos'))
    // A navegação vem numa transição: a tela pode chegar um instante depois do endereço.
    await screen.findByRole('heading', { name: 'Quer ser avisado na hora?' })
    // O "ativado" vem no texto da tela, não no recado flutuante (que cobria a pergunta).
    expect(screen.getByText('Pronto, o apartamento está ativado.')).toBeTruthy()
    expect(screen.getByRole('status').textContent).toBe('')
    expect(localStorage.getItem(CHAVE_OFERTA)).toBe('1')
  })

  it('explica cada passo em uma linha e deixa ir para o mural sem fazer nada', async () => {
    aparelhoFalso()
    await abrirOferta()
    expect(screen.getByText(/Dá para fazer depois em/)).toBeTruthy()
    expect(within(cartao('Coloque o Portal na tela inicial')).getByText(/abre como um aplicativo/)).toBeTruthy()
    expect(within(cartao('Ative as notificações')).getByText(/Só quando sair aviso/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ir para o mural' }).getAttribute('href')).toBe('/avisos')
  })

  it('Chrome no Android oferece instalar com um toque', async () => {
    aparelhoFalso()
    ouvirPedidoDeInstalacao()
    await abrirOferta()
    const pedido = Object.assign(new Event('beforeinstallprompt', { cancelable: true }), {
      prompt: vi.fn(async () => undefined),
      userChoice: Promise.resolve({ outcome: 'accepted' as const }),
    })
    window.dispatchEvent(pedido)
    fireEvent.click(await screen.findByRole('button', { name: 'Instalar na tela inicial' }))
    await waitFor(() => expect(pedido.prompt).toHaveBeenCalled())
    expect(pedido.defaultPrevented).toBe(true)
    await screen.findByText(/Instalado\. Procure o ícone Capibaribe/)
  })

  it('Android sem o pedido do navegador: mostra onde fica a opção no menu', async () => {
    aparelhoFalso()
    await abrirOferta()
    expect(screen.getByText(/Toque nos três pontinhos ⋮ do navegador \(no Samsung, nas três linhas ☰, embaixo\)/)).toBeTruthy()
  })

  it('iPhone no Safari: passo a passo e o aviso de que só chega pelo ícone', async () => {
    aparelhoFalso({ ua: UA.iphone, push: false })
    await abrirOferta()
    const instalar = cartao('Coloque o Portal na tela inicial')
    const passos = within(instalar).getAllByRole('listitem').map((li) => li.textContent)
    expect(passos).toEqual([
      'Toque em Compartilhar (o quadrado com a seta para cima). Se não aparecer, toque antes nos três pontinhos •••.',
      'Role a lista e toque em Adicionar à Tela de Início.',
      'Toque em Adicionar, no canto de cima.',
      'Abra o Portal pelo ícone novo, Capibaribe. Se pedir, entre de novo com bloco, apartamento e senha.',
      'Lá dentro, toque em Ativar notificações.',
    ])
    // O Safari tira a semântica de lista de `list-style: none`: o role volta explícito.
    expect(within(instalar).getByRole('list').getAttribute('role')).toBe('list')
    expect(within(instalar).getByText(/as notificações só chegam se o Portal for aberto pelo ícone/)).toBeTruthy()
    const notificacoes = cartao('Ative as notificações')
    expect(await within(notificacoes).findByText(/Instale e abra pelo ícone novo/)).toBeTruthy()
    expect(within(notificacoes).queryByRole('button')).toBeNull()
  })

  it('iPhone em outro navegador: lembra de abrir no Safari', async () => {
    aparelhoFalso({ ua: UA.iphoneChrome, push: false })
    await abrirOferta()
    expect(screen.getByText(/abra este endereço no Safari/)).toBeTruthy()
  })

  it('já aberto pelo ícone: diz que está pronto', async () => {
    aparelhoFalso({ ua: UA.iphone, instalado: true })
    await abrirOferta()
    expect(screen.getByText('Pronto: o Portal já está na tela inicial.')).toBeTruthy()
  })

  it('no computador: diz computador e onde fica o botão de instalar', async () => {
    aparelhoFalso({ ua: UA.computador })
    await abrirOferta()
    expect(screen.getByRole('heading', { name: 'Coloque o Portal no computador' })).toBeTruthy()
    expect(screen.getByText(/ícone de tela com seta, no fim da barra de endereço/)).toBeTruthy()
  })

  it('ativar daqui pede a permissão, guarda e mostra ligado', async () => {
    const { pedirPermissao } = aparelhoFalso()
    const { chamadas } = await abrirOferta(LIGADO(), {
      'PUT /api/notificacoes/este-aparelho': json(204),
    })
    fireEvent.click(await screen.findByRole('button', { name: 'Ativar notificações' }))
    await screen.findByText('Ligadas neste aparelho.')
    expect(pedirPermissao).toHaveBeenCalled()
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(true)
  })

  it('servidor sem notificações: some o cartão de ativar, fica o de instalar', async () => {
    aparelhoFalso()
    await abrirOferta(DESLIGADO)
    await waitFor(() =>
      expect(screen.queryByRole('heading', { name: 'Ative as notificações' })).toBeNull(),
    )
    expect(screen.getByRole('heading', { name: 'Coloque o Portal na tela inicial' })).toBeTruthy()
  })
})

// --- Minha unidade ------------------------------------------------------------------------------

function dados(): MinhaUnidade {
  return {
    unidade: { login: '1203', bloco: 1, apartamento: '203' },
    responsavel_nome: 'Rafael',
    celular: '81912345678',
    email: null,
    papeis: [],
    ativada_em: '2026-10-01T12:00:00Z',
    aparelhos: [],
  }
}

async function abrirMinhaUnidade(estado: Response, extra: Parameters<typeof apiFalsa>[0] = {}) {
  const chamadas = apiFalsa({
    ...LOGADA,
    'GET /api/minha-unidade': json(200, dados()),
    'GET /api/notificacoes': estado,
    ...extra,
  })
  abrir('/minha-unidade')
  await screen.findByRole('heading', { name: 'Notificações' })
  return chamadas
}

const secao = () => screen.getByRole('region', { name: 'Notificações' })

describe('Minha unidade · Notificações', () => {
  it('desligadas: um toque ativa, com recado', async () => {
    aparelhoFalso()
    await abrirMinhaUnidade(LIGADO(), { 'PUT /api/notificacoes/este-aparelho': json(204) })
    expect(await within(secao()).findByText('Desligadas neste aparelho.')).toBeTruthy()
    fireEvent.click(await within(secao()).findByRole('button', { name: 'Ativar notificações' }))
    await within(secao()).findByText('Ligadas neste aparelho.')
    expect(screen.getAllByRole('status').some((s) => s.textContent === 'Notificações ativadas neste aparelho.')).toBe(true)
  })

  it('ligadas: desativar neste aparelho apaga a inscrição', async () => {
    localStorage.setItem(CHAVE_DONO, '1203')
    const atual = inscricaoFalsa()
    aparelhoFalso({ permissao: 'granted', inscricao: atual })
    const chamadas = await abrirMinhaUnidade(LIGADO(true), {
      'DELETE /api/notificacoes/este-aparelho': json(204),
    })
    fireEvent.click(await within(secao()).findByRole('button', { name: 'Desativar neste aparelho' }))
    await within(secao()).findByText('Desligadas neste aparelho.')
    expect(atual.unsubscribe).toHaveBeenCalled()
    expect(chamadas.some((c) => c.metodo === 'DELETE')).toBe(true)
  })

  it('a API recusou (10 aparelhos): mostra a mensagem e continua desligada', async () => {
    aparelhoFalso()
    const mensagem = 'Este apartamento já tem 10 aparelhos com notificação. Desative em algum deles.'
    await abrirMinhaUnidade(LIGADO(), {
      'PUT /api/notificacoes/este-aparelho': json(409, { codigo: 'limite_de_aparelhos', mensagem }),
    })
    fireEvent.click(await within(secao()).findByRole('button', { name: 'Ativar notificações' }))
    expect((await within(secao()).findByRole('alert')).textContent).toContain(mensagem)
    expect(within(secao()).getByText('Desligadas neste aparelho.')).toBeTruthy()
  })

  it('fechou o pedido sem responder: continua desligada, sem bronca', async () => {
    aparelhoFalso({ resposta: 'default' })
    await abrirMinhaUnidade(LIGADO())
    fireEvent.click(await within(secao()).findByRole('button', { name: 'Ativar notificações' }))
    await within(secao()).findByText('Tudo bem. Dá para ativar depois, aqui mesmo.')
  })

  it('negou: explica como liberar no aparelho', async () => {
    aparelhoFalso({ ua: UA.android, permissao: 'denied' })
    await abrirMinhaUnidade(LIGADO())
    expect(await within(secao()).findByText('As notificações estão bloqueadas neste aparelho.')).toBeTruthy()
    expect(within(secao()).getByText(/ícone à esquerda do endereço do site/)).toBeTruthy()
    expect(within(secao()).queryByRole('button', { name: 'Ativar notificações' })).toBeNull()
  })

  it('liberou nos ajustes: "Já liberei" confere de novo', async () => {
    const { estadoPermissao } = aparelhoFalso({ ua: UA.android, permissao: 'denied' })
    await abrirMinhaUnidade(LIGADO())
    const botao = await within(secao()).findByRole('button', { name: 'Já liberei' })
    estadoPermissao.valor = 'default'
    fireEvent.click(botao)
    await within(secao()).findByText('Desligadas neste aparelho.')
  })

  it('navegador sem suporte: diz o que fazer, em qualquer aparelho', async () => {
    aparelhoFalso({ ua: UA.computador, push: false })
    await abrirMinhaUnidade(LIGADO())
    expect(
      await within(secao()).findByText(
        'Este navegador não recebe notificações. Abra o Portal no Chrome, no Edge ou no Firefox. Os avisos continuam no mural.',
      ),
    ).toBeTruthy()
  })

  it('o navegador recusou a inscrição (aba anônima): explica sem mandar tentar depois', async () => {
    const { pushManager } = aparelhoFalso()
    pushManager.subscribe.mockRejectedValueOnce(new DOMException('negado', 'NotAllowedError'))
    await abrirMinhaUnidade(LIGADO())
    fireEvent.click(await within(secao()).findByRole('button', { name: 'Ativar notificações' }))
    expect((await within(secao()).findByRole('alert')).textContent).toContain(
      'Este navegador não deixou ligar as notificações. Se estiver numa aba anônima, abra o Portal numa aba normal ou no Chrome. Os avisos continuam no mural.',
    )
  })

  it('aberto pelo ícone: não mostra "Como instalar"', async () => {
    aparelhoFalso({ instalado: true })
    await abrirMinhaUnidade(LIGADO())
    await within(secao()).findByText('Desligadas neste aparelho.')
    expect(within(secao()).queryByRole('link', { name: /Como instalar/ })).toBeNull()
  })

  it('sair deste aparelho desfaz a inscrição do navegador (a próxima unidade não herda)', async () => {
    const atual = inscricaoFalsa()
    aparelhoFalso({ permissao: 'granted', inscricao: atual })
    localStorage.setItem(CHAVE_DONO, '1203')
    await abrirMinhaUnidade(LIGADO(true), { 'POST /api/acesso/sair': json(204) })
    fireEvent.click(await screen.findByRole('button', { name: /Sair deste aparelho/ }))
    await waitFor(() => expect(atual.unsubscribe).toHaveBeenCalled())
    expect(localStorage.getItem(CHAVE_DONO)).toBeNull()
  })

  it('iPhone com iOS antigo: diz que precisa atualizar', async () => {
    aparelhoFalso({ ua: UA.iphone, instalado: true, push: false })
    await abrirMinhaUnidade(LIGADO())
    expect(await within(secao()).findByText(/iOS 16.4 ou mais novo/)).toBeTruthy()
  })

  it('entrou de novo neste aparelho: volta a receber sozinho', async () => {
    localStorage.setItem(CHAVE_DONO, '1203')
    aparelhoFalso({ permissao: 'granted', inscricao: inscricaoFalsa() })
    const chamadas = await abrirMinhaUnidade(LIGADO(false), {
      'PUT /api/notificacoes/este-aparelho': json(204),
    })
    await within(secao()).findByText('Ligadas neste aparelho.')
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(true)
  })

  it('sempre tem o caminho para instalar; sem notificações no servidor, só ele', async () => {
    aparelhoFalso()
    await abrirMinhaUnidade(DESLIGADO)
    await waitFor(() => expect(within(secao()).queryByText(/Conferindo/)).toBeNull())
    const link = within(secao()).getByRole('link', { name: 'Como instalar o Portal na tela inicial' })
    expect(link.getAttribute('href')).toBe('/receber-avisos')
    expect(within(secao()).queryByRole('button')).toBeNull()
  })
})

// --- faixa no mural -----------------------------------------------------------------------------

async function abrirMural(estado: Response, extra: Parameters<typeof apiFalsa>[0] = {}) {
  const chamadas = apiFalsa({
    ...LOGADA,
    'GET /api/avisos': json(200, { itens: [] }),
    'GET /api/notificacoes': estado,
    ...extra,
  })
  abrir('/avisos')
  await screen.findByText('Nenhum aviso publicado ainda.')
  return chamadas
}

const FALTA = 'Falta um passo: ative as notificações para saber dos avisos na hora.'

describe('Mural · faixa "Falta um passo"', () => {
  it('aparece para quem pode ativar e ainda não ativou; ativa direto do toque', async () => {
    const { pedirPermissao } = aparelhoFalso({ instalado: true })
    const chamadas = await abrirMural(LIGADO(), { 'PUT /api/notificacoes/este-aparelho': json(204) })
    const faixa = await screen.findByRole('region', { name: 'Notificações' })
    expect(within(faixa).getByText(FALTA)).toBeTruthy()
    fireEvent.click(within(faixa).getByRole('button', { name: 'Ativar' }))
    expect(pedirPermissao).toHaveBeenCalled()
    await within(faixa).findByText('Pronto. Os avisos vão chegar neste aparelho.')
    expect(chamadas.some((c) => c.metodo === 'PUT')).toBe(true)
  })

  it('"Agora não" esconde por 30 dias neste aparelho', async () => {
    aparelhoFalso()
    await abrirMural(LIGADO())
    fireEvent.click(await screen.findByRole('button', { name: 'Agora não' }))
    expect(screen.queryByText(FALTA)).toBeNull()
    const ate = Number(localStorage.getItem(CHAVE_FAIXA))
    expect(Math.round((ate - Date.now()) / 86_400_000)).toBe(30)
  })

  it('dispensada há menos de 30 dias: não aparece; depois, volta', async () => {
    aparelhoFalso()
    localStorage.setItem(CHAVE_FAIXA, String(Date.now() + 86_400_000))
    await abrirMural(LIGADO())
    await waitFor(() => expect(screen.queryByText(FALTA)).toBeNull())
    cleanup()
    localStorage.setItem(CHAVE_FAIXA, String(Date.now() - 1))
    await abrirMural(LIGADO())
    expect(await screen.findByText(FALTA)).toBeTruthy()
  })

  it.each([
    ['já ativou', LIGADO(true), { permissao: 'granted' as const, inscricao: inscricaoFalsa() }],
    ['servidor desligado', DESLIGADO, {}],
    ['permissão negada', LIGADO(), { permissao: 'denied' as const }],
    ['iPhone fora do ícone', LIGADO(), { ua: UA.iphone, push: false }],
    ['sem suporte', LIGADO(), { ua: UA.computador, push: false }],
  ])('não aparece: %s', async (_nome, estado, aparelho) => {
    localStorage.setItem(CHAVE_DONO, '1203')
    aparelhoFalso(aparelho)
    await abrirMural(estado)
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.queryByText(FALTA)).toBeNull()
  })
})
