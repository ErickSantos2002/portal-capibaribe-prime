// M3 · Épico B: a lógica dos anexos do aviso (spec `m3-anexos.md`, seção 3.1).
import { describe, expect, it } from 'vitest'
import {
  descricaoDoAnexo,
  ehFoto,
  idsProntos,
  quantosAnexos,
  situacaoDosAnexos,
  tamanhoEmTexto,
  type ItemAnexo,
} from './anexos'

const MB = 1024 * 1024

function item(situacao: ItemAnexo['situacao'], id = 1): ItemAnexo {
  return {
    chave: `k${id}`,
    nome: `arquivo ${id}.pdf`,
    tipo: 'application/pdf',
    previa: null,
    situacao,
    arquivo:
      situacao === 'pronto'
        ? { id, nome: `arquivo ${id}.pdf`, tipo: 'application/pdf', tamanho_bytes: 1000 }
        : undefined,
  }
}

describe('textos dos anexos', () => {
  it('tamanho como a pessoa entende', () => {
    expect(tamanhoEmTexto(200)).toBe('1 KB')
    expect(tamanhoEmTexto(320 * 1024)).toBe('320 KB')
    expect(tamanhoEmTexto(1023 * 1024)).toBe('1.023 KB')
    expect(tamanhoEmTexto(1.24 * MB)).toBe('1,2 MB')
    expect(tamanhoEmTexto(10 * MB)).toBe('10 MB')
  })

  it('foto ou PDF', () => {
    expect(ehFoto('image/webp')).toBe(true)
    expect(ehFoto('application/pdf')).toBe(false)
    expect(
      descricaoDoAnexo({ id: 1, nome: 'a', tipo: 'application/pdf', tamanho_bytes: 320 * 1024 }),
    ).toBe('PDF, 320 KB')
    expect(
      descricaoDoAnexo({ id: 1, nome: 'a', tipo: 'image/jpeg', tamanho_bytes: 1.24 * MB }),
    ).toBe('Foto, 1,2 MB')
  })

  it('quantos anexos, no singular e no plural', () => {
    expect(quantosAnexos(1)).toBe('1 anexo')
    expect(quantosAnexos(3)).toBe('3 anexos')
  })
})

describe('situação dos anexos ao publicar', () => {
  it('sem anexo ou tudo pronto: pode publicar', () => {
    expect(situacaoDosAnexos([])).toEqual({ pode: true, mensagem: '' })
    expect(situacaoDosAnexos([item('pronto', 1), item('pronto', 2)]).pode).toBe(true)
  })

  it('enviando: espera', () => {
    expect(situacaoDosAnexos([item('pronto'), item('enviando', 2)])).toEqual({
      pode: false,
      mensagem: 'Espere os arquivos terminarem de enviar.',
    })
  })

  it('com erro: tirar ou enviar de novo', () => {
    expect(situacaoDosAnexos([item('erro'), item('enviando', 2)])).toEqual({
      pode: false,
      mensagem: 'Tire ou envie de novo o arquivo que deu erro.',
    })
  })

  it('os ids na ordem da lista, só os prontos', () => {
    expect(idsProntos([item('pronto', 7), item('erro', 8), item('pronto', 3)])).toEqual([7, 3])
  })
})
