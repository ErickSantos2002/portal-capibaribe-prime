// M5 · revisões (U3): a confirmação que abre na tela vai para o meio dela; mas, se o bloco é mais
// alto que a tela (letra grande), centralizar cortava o começo, onde estão o título e a pergunta.
// Aí ele vai para o alto da tela.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { centralizar } from './rolar'

function bloco(altura: number) {
  const el = document.createElement('div')
  el.tabIndex = -1
  el.getBoundingClientRect = () => ({ height: altura, top: 0, bottom: altura, left: 0, right: 0, width: 300, x: 0, y: 0, toJSON: () => ({}) })
  const rolar = vi.fn()
  el.scrollIntoView = rolar
  document.body.append(el)
  return { el, rolar }
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('centralizar', () => {
  it('bloco que cabe na tela vai para o meio', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 780 })
    const { el, rolar } = bloco(300)
    centralizar(el)
    expect(rolar).toHaveBeenCalledWith(expect.objectContaining({ block: 'center' }))
  })

  it('bloco mais alto que a tela vai para o alto (o começo não some)', () => {
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 780 })
    const { el, rolar } = bloco(900)
    centralizar(el)
    expect(rolar).toHaveBeenCalledWith(expect.objectContaining({ block: 'start' }))
  })

  it('leva o foco ao bloco sem rolar de novo', () => {
    const { el } = bloco(100)
    centralizar(el)
    expect(document.activeElement).toBe(el)
  })
})
