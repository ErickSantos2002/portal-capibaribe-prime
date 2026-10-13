// M3 · Épico B: a fila de envio do formulário (revisão de código, C3 e C6).
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ArquivoEnviado } from '../arquivos/tipos'
import { useAnexos } from './useAnexos'

const enviarArquivo = vi.hoisted(() => vi.fn())
vi.mock('../arquivos/enviar', () => ({ enviarArquivo }))

const PDF: ArquivoEnviado = { id: 1, nome: 'a.pdf', tipo: 'application/pdf', tamanho_bytes: 10 }
const arquivo = (nome: string) => new File(['x'], nome, { type: 'application/pdf' })

beforeEach(() => {
  enviarArquivo.mockReset()
})

describe('useAnexos', () => {
  it('C3: saiu da tela, nada novo é enviado', async () => {
    let terminar: (a: ArquivoEnviado) => void = () => {}
    enviarArquivo.mockImplementationOnce(() => new Promise((r) => (terminar = r)))
    enviarArquivo.mockResolvedValue(PDF)
    const { result, unmount } = renderHook(() => useAnexos())
    act(() => {
      result.current.adicionar([arquivo('a.pdf'), arquivo('b.pdf'), arquivo('c.pdf')])
    })
    await act(async () => {})
    expect(enviarArquivo).toHaveBeenCalledTimes(1)
    unmount()
    await act(async () => terminar(PDF))
    await act(async () => {})
    expect(enviarArquivo).toHaveBeenCalledTimes(1)
  })

  it('C6: a conta das vagas vale na hora, também depois de tirar', () => {
    enviarArquivo.mockReturnValue(new Promise(() => {}))
    const { result } = renderHook(() => useAnexos())
    let fora: string[] = []
    act(() => {
      fora = result.current.adicionar(['1', '2', '3'].map((n) => arquivo(`${n}.pdf`)))
    })
    expect(fora).toEqual([])
    const primeira = result.current.itens[0].chave
    act(() => {
      result.current.tirar(primeira)
      // Tirar de novo o mesmo não abre outra vaga.
      result.current.tirar(primeira)
      fora = result.current.adicionar(['4', '5', '6', '7'].map((n) => arquivo(`${n}.pdf`)))
    })
    expect(fora).toEqual(['7.pdf'])
    expect(result.current.itens).toHaveLength(5)
  })
})
