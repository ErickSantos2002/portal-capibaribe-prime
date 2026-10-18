// M5 · revisões (R1): o detector de "letra grande" marca o <html> pelo tamanho que o navegador
// deu à raiz, que é o que acompanha o Dynamic Type do iPhone (media query em em não acompanha:
// Media Queries 4, §1.3). Ver duvidas-m5-letra.md, seção Revisões.
import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { classificar, useLetraGrande, vigiarLetra } from './letra'

const raiz = document.documentElement

function letra(px: string) {
  raiz.style.fontSize = px
}

let parar: (() => void) | undefined

beforeEach(() => {
  letra('16px')
  Object.defineProperty(window, 'innerHeight', { configurable: true, value: 780 })
})

afterEach(() => {
  parar?.()
  parar = undefined
  cleanup()
  raiz.style.fontSize = ''
  delete raiz.dataset.letra
  delete raiz.dataset.altura
  delete raiz.dataset.largura
})

describe('classificar', () => {
  it('letra de fábrica (16), o padrão do iPhone (17) e um passo acima (19) não são grandes', () => {
    expect(classificar(16, 780).grande).toBe(false)
    expect(classificar(17, 780).grande).toBe(false)
    expect(classificar(19.9, 780).grande).toBe(false)
  })

  it('a partir de 20 px (125 %) é grande', () => {
    expect(classificar(20, 780).grande).toBe(true)
    expect(classificar(32, 780).grande).toBe(true)
  })

  it('tela baixa: menos de 35 letras de altura (560 px com a de fábrica)', () => {
    expect(classificar(16, 780).baixa).toBe(false)
    expect(classificar(16, 559).baixa).toBe(true)
    expect(classificar(32, 1000).baixa).toBe(true)
    expect(classificar(32, 1120).baixa).toBe(false)
  })
})

describe('classificar: tela estreita (barra do celular, "Docs")', () => {
  it('abaixo de 340 px de largura é estreita, e a letra não interfere', () => {
    expect(classificar(16, 800, 320).estreita).toBe(true)
    expect(classificar(32, 800, 360).estreita).toBe(false)
    expect(classificar(16, 800, 340).estreita).toBe(false)
  })
})

describe('vigiarLetra', () => {
  it('marca data-largura="estreita" pela largura da janela e tira quando ela passa', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 412 })
    parar = vigiarLetra()
    expect(raiz.dataset.largura).toBeUndefined()
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 320 })
    window.dispatchEvent(new Event('resize'))
    expect(raiz.dataset.largura).toBe('estreita')
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 412 })
    window.dispatchEvent(new Event('resize'))
    expect(raiz.dataset.largura).toBeUndefined()
  })

  it('marca o html na hora: letra de fábrica sem marca, letra grande com data-letra', () => {
    parar = vigiarLetra()
    expect(raiz.dataset.letra).toBeUndefined()
    parar()
    letra('24px')
    parar = vigiarLetra()
    expect(raiz.dataset.letra).toBe('grande')
  })

  it('acompanha a mudança de letra (a régua de 1rem muda de largura)', () => {
    const observados: Array<() => void> = []
    class Observador {
      constructor(cb: () => void) {
        observados.push(cb)
      }
      observe() {}
      disconnect() {}
    }
    const original = globalThis.ResizeObserver
    globalThis.ResizeObserver = Observador as unknown as typeof ResizeObserver
    try {
      parar = vigiarLetra()
      expect(raiz.dataset.letra).toBeUndefined()
      letra('32px')
      observados.forEach((cb) => cb())
      expect(raiz.dataset.letra).toBe('grande')
      letra('16px')
      observados.forEach((cb) => cb())
      expect(raiz.dataset.letra).toBeUndefined()
    } finally {
      globalThis.ResizeObserver = original
    }
  })

  it('acompanha a altura da janela (celular deitado)', () => {
    parar = vigiarLetra()
    expect(raiz.dataset.altura).toBeUndefined()
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 400 })
    window.dispatchEvent(new Event('resize'))
    expect(raiz.dataset.altura).toBe('baixa')
  })

  it('parar tira a régua da página', () => {
    parar = vigiarLetra()
    expect(document.querySelectorAll('.regua-letra')).toHaveLength(1)
    parar()
    parar = undefined
    expect(document.querySelectorAll('.regua-letra')).toHaveLength(0)
  })
})

describe('useLetraGrande', () => {
  function Mostra() {
    return <p>{useLetraGrande() ? 'grande' : 'fábrica'}</p>
  }

  it('o componente troca quando a letra muda', () => {
    parar = vigiarLetra()
    const { container } = render(<Mostra />)
    expect(container.textContent).toBe('fábrica')
    letra('24px')
    act(() => {
      window.dispatchEvent(new Event('resize'))
    })
    expect(container.textContent).toBe('grande')
  })
})
