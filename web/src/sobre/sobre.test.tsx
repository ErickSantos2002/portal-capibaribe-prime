// Logo na entrada e a janela "Versão 1.1.0" com o que mudou.
import { act, cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import { NOVIDADES, VERSAO } from './novidades'

// O jsdom ainda não tem showModal/close; o comportamento de verdade (inerte, Tab, Esc nativo) é
// conferido no navegador (Playwright). Aqui só o que o componente faz.
beforeAll(() => {
  const proto = HTMLDialogElement.prototype
  proto.showModal ??= function (this: HTMLDialogElement) {
    this.open = true
  }
  proto.close ??= function (this: HTMLDialogElement) {
    if (!this.open) return
    this.open = false
    this.dispatchEvent(new Event('close'))
  }
})

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const NOME_DO_BOTAO = `Versão ${VERSAO}`

function janela(): HTMLDialogElement {
  return screen.getByRole('dialog', { hidden: true }) as HTMLDialogElement
}

/** Fechada, a janela sai do DOM. */
function semJanela() {
  expect(screen.queryByRole('dialog', { hidden: true })).toBeNull()
}

describe('logo na entrada', () => {
  it('mostra o logo do residencial, mantém o h1 e não tem mais a placa da marca', async () => {
    apiFalsa({})
    abrir('/entrar')
    const logo = (await screen.findByRole('img', {
      name: 'Capibaribe Prime Residence',
    })) as HTMLImageElement
    expect(logo.srcset).toMatch(/2x/)
    expect(logo.getAttribute('width')).toBeTruthy()
    expect(logo.getAttribute('height')).toBeTruthy()
    expect(screen.getByRole('heading', { level: 1, name: 'Portal Capibaribe Prime' })).toBeTruthy()
    expect(document.querySelector('.placa.marca')).toBeNull()
  })
})

describe('janela de versão', () => {
  it('a entrada tem o botão da versão no rodapé', async () => {
    apiFalsa({})
    abrir('/entrar')
    const botao = await screen.findByRole('button', { name: NOME_DO_BOTAO })
    expect(botao.closest('footer')).toBeTruthy()
  })

  it('abre a janela com o título ligado, o logo e o que mudou em cada versão', async () => {
    apiFalsa({})
    abrir('/entrar')
    fireEvent.click(await screen.findByRole('button', { name: NOME_DO_BOTAO }))
    const dialogo = janela()
    expect(dialogo.open).toBe(true)
    expect(dialogo.getAttribute('aria-modal')).toBe('true')
    const titulo = document.getElementById(dialogo.getAttribute('aria-labelledby')!)
    expect(titulo?.textContent).toBe(NOME_DO_BOTAO)
    const dentro = within(dialogo)
    expect(dentro.getByRole('img', { name: 'Capibaribe Prime Residence', hidden: true })).toBeTruthy()
    expect(dentro.getByRole('heading', { name: 'O que mudou', hidden: true })).toBeTruthy()
    for (const novidade of NOVIDADES) {
      expect(
        dentro.getByRole('heading', { level: 4, name: new RegExp(`^${novidade.versao}`), hidden: true }),
      ).toBeTruthy()
      for (const item of novidade.itens) expect(dentro.getByText(item)).toBeTruthy()
    }
    expect(dentro.getAllByText('6 de outubro de 2026').length).toBeGreaterThan(0)
  })

  it('"Fechar" fecha e devolve o foco ao botão de origem', async () => {
    apiFalsa({})
    abrir('/entrar')
    const botao = await screen.findByRole('button', { name: NOME_DO_BOTAO })
    botao.focus()
    fireEvent.click(botao)
    fireEvent.click(within(janela()).getByRole('button', { name: 'Fechar', hidden: true }))
    semJanela()
    await waitFor(() => expect(document.activeElement).toBe(botao))
  })

  it('Esc (o evento cancel do diálogo) fecha e devolve o foco', async () => {
    apiFalsa({})
    abrir('/entrar')
    const botao = await screen.findByRole('button', { name: NOME_DO_BOTAO })
    fireEvent.click(botao)
    // No navegador, Esc dispara `cancel` e depois fecha; aqui fazemos o mesmo à mão.
    fireEvent(janela(), new Event('cancel', { cancelable: true }))
    act(() => janela().close())
    semJanela()
    await waitFor(() => expect(document.activeElement).toBe(botao))
  })

  it('o Tab dá a volta dentro da janela (não vai para a barra do navegador)', async () => {
    apiFalsa({})
    abrir('/entrar')
    fireEvent.click(await screen.findByRole('button', { name: NOME_DO_BOTAO }))
    const dialogo = janela()
    const fechar = within(dialogo).getByRole('button', { name: 'Fechar', hidden: true })
    const rolagem = dialogo.querySelector<HTMLElement>('.janela-rolagem')!
    fechar.focus()
    fireEvent.keyDown(fechar, { key: 'Tab' })
    expect(document.activeElement).toBe(rolagem)
    fireEvent.keyDown(rolagem, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(fechar)
  })

  it('clicar fora da janela (no fundo escurecido) fecha', async () => {
    apiFalsa({})
    abrir('/entrar')
    fireEvent.click(await screen.findByRole('button', { name: NOME_DO_BOTAO }))
    fireEvent.click(janela())
    semJanela()
  })

  it('logado: no menu lateral e no fim de Minha unidade', async () => {
    apiFalsa({
      'GET /api/acesso/eu': json(200, eu()),
      'GET /api/minha-unidade': json(200, {
        unidade: { login: '1203', bloco: 1, apartamento: '203' },
        responsavel_nome: 'Rafael',
        celular: '81912345678',
        email: null,
        papeis: [],
        ativada_em: '2026-10-01T12:00:00Z',
        aparelhos: [],
      }),
    })
    abrir('/minha-unidade')
    await screen.findByText('Rafael')
    const botoes = screen.getAllByRole('button', { name: NOME_DO_BOTAO })
    expect(botoes).toHaveLength(2)
    expect(botoes.some((b) => b.closest('nav'))).toBe(true)
    expect(botoes.some((b) => b.closest('main'))).toBe(true)
    // Os dois botões abrem a janela; uma janela por botão, nunca duas abertas.
    fireEvent.click(botoes[1])
    expect(screen.getAllByRole('dialog', { hidden: true })).toHaveLength(1)
  })
})
