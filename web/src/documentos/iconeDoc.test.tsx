// M5 · letra que cresce (spec m5-letra, seção 3.4): o ícone dos documentos cresce com a letra.
// O `tamanho` continua em px de desenho (24 = o tamanho com a letra de fábrica) e vira rem.
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { IconeDoc } from './pecas'

afterEach(cleanup)

describe('ícone dos documentos', () => {
  it('mede em rem: 24 vira 1.5rem', () => {
    const { container } = render(<IconeDoc nome="baixar" />)
    const svg = container.querySelector('svg')!
    // Revisões do M5 (R3): atributo em número, rem pelo CSS (`.icone` e `--icone`).
    expect(svg.getAttribute('width')).toBe('24')
    expect(svg.getAttribute('height')).toBe('24')
    expect(svg.classList.contains('icone')).toBe(true)
    expect(svg.style.getPropertyValue('--icone')).toBe('1.5rem')
  })

  it('o tamanho pedido também: 20 vira 1.25rem', () => {
    const { container } = render(<IconeDoc nome="fora" tamanho={20} />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('height')).toBe('20')
    expect(svg.style.getPropertyValue('--icone')).toBe('1.25rem')
  })
})
