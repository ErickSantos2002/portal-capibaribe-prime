// A folha do Menu (spec docs/superpowers/specs/2026-10-18-navegacao-bola-design.md, seção 4): sobe
// de baixo com todos os lugares, cada um com nome e frase, e fecha pela bola-X, pelo véu, pelo
// Esc e pelo voltar do Android (os dois chegam como `cancel` + `close` do <dialog>), sem mexer no
// histórico. Tocar num lugar navega e fecha.
import { act, cleanup, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { abrir, apiFalsa, eu, json } from '../acesso/apoioDeTeste'
import type { Eu } from '../api/tipos'

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

function api(quem: Eu, naoLidos = 0) {
  apiFalsa({
    'GET /api/acesso/eu': json(200, quem),
    'GET /api/avisos/nao-lidos': json(200, { quantidade: naoLidos }),
  })
}

async function bola(): Promise<HTMLElement> {
  await screen.findByRole('navigation', { name: 'Seções do Portal' })
  return within(document.querySelector<HTMLElement>('.nav-barra')!).getByRole('button', { name: 'Menu' })
}

async function abrirFolha(): Promise<HTMLElement> {
  fireEvent.click(await bola())
  return screen.findByRole('dialog', { name: 'Para onde você quer ir?' })
}

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('abrir', () => {
  it('a bola abre a folha, com o foco no título, e fica aria-expanded', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    expect((folha as HTMLDialogElement).open).toBe(true)
    const titulo = within(folha).getByRole('heading', { name: 'Para onde você quer ir?' })
    await waitFor(() => expect(document.activeElement).toBe(titulo))
    expect((await bola()).getAttribute('aria-expanded')).toBe('true')
  })

  it('o admin vê os grupos Dia a dia e Gestão, e 7 lugares com nome e frase', async () => {
    api(eu(['admin']))
    abrir('/avisos')
    const folha = await abrirFolha()
    const grupos = within(folha).getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(grupos).toEqual(['Dia a dia', 'Gestão'])
    const links = within(folha).getAllByRole('link')
    expect(links).toHaveLength(7)
    expect(links[1].textContent).toContain('Enquetes')
    expect(links[1].textContent).toContain('Vote pela sua unidade')
    // Indicações (spec das indicações, seção 3.4): só na folha, entre Documentos e Minha unidade.
    expect(links[3].textContent).toContain('Indicações')
    expect(links[3].textContent).toContain('Serviços que os vizinhos recomendam')
    // Classificados (spec dos classificados, seção 3.4): logo depois de Indicações.
    expect(links[4].textContent).toContain('Classificados')
    expect(links[4].textContent).toContain('Vender, trocar ou doar entre vizinhos')
    expect(links[6].textContent).toContain('Unidades')
    expect(links[6].textContent).toContain('Quem já entrou e os contatos')
  })

  it('o morador não tem o grupo Gestão', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    expect(within(folha).queryByRole('heading', { name: 'Gestão' })).toBeNull()
    expect(within(folha).getAllByRole("link")).toHaveLength(6)
  })

  it('o lugar atual: aria-current, "Você está aqui" e o contador de não lidos', async () => {
    api(eu(), 2)
    abrir('/avisos')
    await screen.findAllByLabelText('2 não lidos')
    const folha = await abrirFolha()
    const avisos = within(folha).getByRole('link', { name: /Avisos/ })
    expect(avisos.getAttribute('aria-current')).toBe('page')
    expect(avisos.textContent).toContain('Você está aqui')
    expect(avisos.textContent).not.toContain('Recados da Comissão e da obra')
    expect(within(avisos).getByLabelText('2 não lidos')).toBeTruthy()
  })

  it('a pegadinha é só visual (aria-hidden)', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    expect(folha.querySelector('.menu-folha-pega')?.getAttribute('aria-hidden')).toBe('true')
  })
})

describe('fechar', () => {
  it('a bola-X "Fechar" fica dentro da folha; fecha e devolve o foco para "Menu"', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    fireEvent.click(within(folha).getByRole('button', { name: 'Fechar' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    const menu = await bola()
    expect(document.activeElement).toBe(menu)
    expect(menu.getAttribute('aria-expanded')).toBe('false')
  })

  it('Esc e o voltar do Android (cancel + close do dialog) fecham, sem mexer no histórico', async () => {
    api(eu())
    const antes = window.history.length
    const roteador = abrir('/avisos')
    const folha = (await abrirFolha()) as HTMLDialogElement
    expect(window.history.length).toBe(antes)
    act(() => {
      folha.dispatchEvent(new Event('cancel', { cancelable: true }))
      folha.close()
    })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(roteador.state.location.pathname).toBe('/avisos')
    expect(window.history.length).toBe(antes)
  })

  it('tocar no véu (fora da caixa) fecha', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    fireEvent.pointerDown(folha)
    fireEvent.click(folha)
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })

  it('arrastar o dedo (ou o mouse) de dentro da folha até o véu não fecha', async () => {
    // O navegador manda o click para o ancestral comum de onde o dedo desceu e de onde subiu: o
    // próprio <dialog>. Só o toque que também começou no véu fecha.
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    fireEvent.pointerDown(within(folha).getByRole('link', { name: /Enquetes/ }))
    fireEvent.click(folha)
    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('se a tela virar layout de computador com a folha aberta (iPhone que gira), ela fecha', async () => {
    // O ResizeObserver da barra avisa quando ela some (display: none no @container do
    // computador): getClientRects vazio.
    const avisos: (() => void)[] = []
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(avisar: () => void) {
          avisos.push(avisar)
        }
        observe() {}
        disconnect() {}
      },
    )
    api(eu())
    abrir('/avisos')
    await abrirFolha()
    const barra = document.querySelector<HTMLElement>('.nav-barra')!
    const visivel = vi.spyOn(barra, 'getClientRects').mockReturnValue([{}] as unknown as DOMRectList)
    act(() => avisos.forEach((avisar) => avisar()))
    expect(screen.getByRole('dialog')).toBeTruthy()
    visivel.mockReturnValue([] as unknown as DOMRectList)
    act(() => avisos.forEach((avisar) => avisar()))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(document.body.style.position).toBe('')
  })

  it('tocar num lugar navega e fecha; o voltar seguinte leva à tela anterior', async () => {
    api(eu())
    const roteador = abrir('/avisos')
    const folha = await abrirFolha()
    fireEvent.click(within(folha).getByRole('link', { name: /Enquetes/ }))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/enquetes'))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    await act(() => roteador.navigate(-1))
    expect(roteador.state.location.pathname).toBe('/avisos')
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('se a página mudar com a folha aberta (voltar sem CloseWatcher), a folha não fica aberta na outra', async () => {
    api(eu())
    const roteador = abrir('/avisos')
    await abrirFolha()
    await act(() => roteador.navigate('/documentos'))
    await waitFor(() => expect(roteador.state.location.pathname).toBe('/documentos'))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(document.body.style.position).toBe('')
  })

  it('o fundo da página fica travado enquanto a folha está aberta, e volta ao fechar', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    expect(document.body.style.position).toBe('fixed')
    fireEvent.click(within(folha).getByRole('button', { name: 'Fechar' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(document.body.style.position).toBe('')
  })

  it('arrastar a pegadinha para baixo além de um quarto da folha fecha; pouco, volta', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    const caixa = folha.querySelector<HTMLElement>('.menu-folha-caixa')!
    vi.spyOn(caixa, 'getBoundingClientRect').mockReturnValue({ height: 400 } as DOMRect)
    const topo = folha.querySelector<HTMLElement>('.menu-folha-topo')!
    fireEvent.pointerDown(topo, { clientY: 100, pointerId: 1 })
    fireEvent.pointerMove(topo, { clientY: 150, pointerId: 1 })
    fireEvent.pointerUp(topo, { clientY: 150, pointerId: 1 })
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(caixa.style.transform).toBe('')
    fireEvent.pointerDown(topo, { clientY: 100, pointerId: 1 })
    fireEvent.pointerMove(topo, { clientY: 250, pointerId: 1 })
    fireEvent.pointerUp(topo, { clientY: 250, pointerId: 1 })
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  })
})

describe('teclado', () => {
  it('o Tab fica preso na folha: do último (Fechar) volta ao primeiro lugar', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    const fecharBotao = within(folha).getByRole('button', { name: 'Fechar' })
    fecharBotao.focus()
    fireEvent.keyDown(fecharBotao, { key: 'Tab' })
    expect(document.activeElement).toBe(within(folha).getAllByRole('link')[0])
  })

  it('Shift+Tab no título (onde o foco começa) vai para o último (Fechar)', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    const titulo = within(folha).getByRole('heading', { name: 'Para onde você quer ir?' })
    await waitFor(() => expect(document.activeElement).toBe(titulo))
    fireEvent.keyDown(titulo, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(within(folha).getByRole('button', { name: 'Fechar' }))
  })

  it('Shift+Tab no primeiro lugar também vai para o último', async () => {
    api(eu())
    abrir('/avisos')
    const folha = await abrirFolha()
    const primeiro = within(folha).getAllByRole('link')[0]
    primeiro.focus()
    fireEvent.keyDown(primeiro, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(within(folha).getByRole('button', { name: 'Fechar' }))
  })
})

describe('letra grande: a lista rola', () => {
  it('ao abrir, o lugar atual rola para a vista dentro da lista, e o foco fica no título', async () => {
    const rolar = vi.fn()
    Element.prototype.scrollIntoView = rolar
    try {
      api(eu(['admin']))
      abrir('/unidades')
      const folha = await abrirFolha()
      const unidades = within(folha).getByRole('link', { name: /Unidades/ })
      await waitFor(() => expect(rolar).toHaveBeenCalled())
      expect(rolar.mock.contexts.at(-1)).toBe(unidades)
      expect(rolar).toHaveBeenLastCalledWith({ block: 'nearest' })
      expect(document.activeElement).toBe(within(folha).getByRole('heading', { name: 'Para onde você quer ir?' }))
    } finally {
      delete (Element.prototype as Partial<Element>).scrollIntoView
    }
  })

  it('a lista marca quando há mais lugares abaixo e acima (o CSS desenha o fio)', async () => {
    api(eu(['admin']))
    abrir('/avisos')
    const folha = await abrirFolha()
    const lista = folha.querySelector<HTMLElement>('.menu-folha-lista')!
    expect(lista.hasAttribute('data-mais-abaixo')).toBe(false)
    Object.defineProperty(lista, 'scrollHeight', { configurable: true, value: 600 })
    Object.defineProperty(lista, 'clientHeight', { configurable: true, value: 300 })
    fireEvent.scroll(lista)
    expect(lista.hasAttribute('data-mais-abaixo')).toBe(true)
    expect(lista.hasAttribute('data-mais-acima')).toBe(false)
    lista.scrollTop = 300
    fireEvent.scroll(lista)
    expect(lista.hasAttribute('data-mais-abaixo')).toBe(false)
    expect(lista.hasAttribute('data-mais-acima')).toBe(true)
  })
})
