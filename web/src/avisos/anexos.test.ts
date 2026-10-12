// M3 · Épico B: a lógica dos anexos do aviso (spec `m3-anexos.md`, seção 3.1).
import { describe, expect, it } from 'vitest'
import {
  descricaoDoAnexo,
  ehFoto,
  idsProntos,
  mudancaNosAnexos,
  progressoDoEnvio,
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

describe('o que mudou nos anexos na correção (U6)', () => {
  const foto = (id: number) => ({
    id,
    nome: `f${id}.webp`,
    tipo: 'image/webp' as const,
    tamanho_bytes: 1,
  })
  const pdf = (id: number, nome: string) => ({
    id,
    nome,
    tipo: 'application/pdf' as const,
    tamanho_bytes: 1,
  })

  it('entrou e saiu, fotos contadas e PDFs pelo nome', () => {
    expect(mudancaNosAnexos([foto(1), pdf(2, 'A.pdf')], [pdf(2, 'A.pdf'), pdf(3, 'Comunicado.pdf')])).toBe(
      'Anexos: entrou Comunicado.pdf; saiu 1 foto.',
    )
    expect(mudancaNosAnexos([], [foto(1), foto(2), pdf(3, 'B.pdf')])).toBe(
      'Anexos: entraram B.pdf e 2 fotos.',
    )
    expect(mudancaNosAnexos([pdf(1, 'A.pdf'), pdf(2, 'B.pdf'), foto(3)], [])).toBe(
      'Anexos: saíram A.pdf, B.pdf e 1 foto.',
    )
  })

  it('só a ordem, ou nada', () => {
    expect(mudancaNosAnexos([foto(1), foto(2)], [foto(2), foto(1)])).toBe('Anexos: mudou a ordem.')
    expect(mudancaNosAnexos([foto(1)], [foto(1)])).toBeNull()
  })
})

describe('progresso do envio (U3)', () => {
  it('quantos já terminaram dos escolhidos agora, enquanto algum envia', () => {
    expect(progressoDoEnvio([item('pronto', 1)])).toBeNull()
    const ja = { ...item('pronto', 9), jaPublicado: true }
    expect(progressoDoEnvio([ja, item('pronto', 1), item('erro', 2), item('enviando', 3)])).toEqual({
      feitos: 2,
      total: 3,
    })
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
