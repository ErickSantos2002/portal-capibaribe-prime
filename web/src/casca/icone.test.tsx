// M5 · letra que cresce (spec m5-letra, seção 3.4): o ícone ao lado do texto cresce com a letra.
// O `tamanho` continua em px de desenho (24 = o tamanho com a letra de fábrica) e vira rem.
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { Icone } from './Icone'

afterEach(cleanup)

describe('ícone', () => {
  it('mede em rem: 24 vira 1.5rem', () => {
    const { container } = render(<Icone nome="avisos" />)
    const svg = container.querySelector('svg')!
    expect(svg.getAttribute('width')).toBe('1.5rem')
    expect(svg.getAttribute('height')).toBe('1.5rem')
  })

  it('o tamanho pedido também: 18 vira 1.125rem', () => {
    const { container } = render(<Icone nome="busca" tamanho={18} />)
    expect(container.querySelector('svg')!.getAttribute('width')).toBe('1.125rem')
  })
})
