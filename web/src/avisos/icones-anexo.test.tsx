// M5 · letra que cresce (spec m5-letra, seção 3.4): os ícones dos anexos crescem com a letra,
// como o `Icone` da casca. O `tamanho` continua em px de desenho (24 = com a letra de fábrica).
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { IconeAnexo } from './IconesAnexo'

afterEach(cleanup)

describe('ícone dos anexos', () => {
  it('mede em rem: 24 vira 1.5rem', () => {
    const { container } = render(<IconeAnexo nome="clipe" />)
    const svg = container.querySelector('svg')!
    // Revisões do M5 (R3): atributo em número, rem pelo CSS (`.icone` e `--icone`).
    expect(svg.getAttribute('width')).toBe('24')
    expect(svg.getAttribute('height')).toBe('24')
    expect(svg.classList.contains('icone')).toBe(true)
    expect(svg.style.getPropertyValue('--icone')).toBe('1.5rem')
  })

  it('o tamanho pedido também: 28 vira 1.75rem', () => {
    const { container } = render(<IconeAnexo nome="foto" tamanho={28} />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('width')).toBe('28')
    expect(svg.style.getPropertyValue('--icone')).toBe('1.75rem')
  })
})
