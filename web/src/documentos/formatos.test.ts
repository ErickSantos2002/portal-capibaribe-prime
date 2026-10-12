// Épico A do M3 · formatos dos documentos na voz do morador.
import { describe, expect, it } from 'vitest'
import {
  ASSUNTOS,
  agrupar,
  dataDoDocumento,
  filtrar,
  hojeEmRecife,
  tamanhoEmTexto,
  tipoEmTexto,
} from './formatos'
import type { DocumentoResumo } from './tipos'

function doc(id: number, extra: Partial<DocumentoResumo> = {}): DocumentoResumo {
  return {
    id,
    titulo: `Documento ${id}`,
    categoria: 'obra',
    data_documento: '2026-10-01',
    acesso: 'compradores',
    versao: 1,
    atualizado_em: '2026-10-02T12:00:00Z',
    arquivo: { id, nome: 'a.pdf', tipo: 'application/pdf', tamanho_bytes: 1000 },
    arquivado_em: null,
    ...extra,
  }
}

describe('assuntos', () => {
  it('na ordem do formulário, com o nome do grupo no plural quando cabe', () => {
    expect(ASSUNTOS.map((a) => [a.valor, a.nome, a.grupo])).toEqual([
      ['obra', 'Obra', 'Obra'],
      ['convencao', 'Convenção', 'Convenção'],
      ['regimento', 'Regimento', 'Regimento'],
      ['ata', 'Ata', 'Atas'],
      ['contrato', 'Contrato', 'Contratos'],
      ['orientacao', 'Orientação', 'Orientações'],
      ['outro', 'Outro', 'Outros'],
    ])
  })

  it('agrupa na ordem dos assuntos, mantendo a ordem da lista dentro de cada grupo', () => {
    const itens = [
      doc(1, { categoria: 'ata' }),
      doc(2, { categoria: 'obra' }),
      doc(3, { categoria: 'ata' }),
    ]
    expect(agrupar(itens).map((g) => [g.assunto.grupo, g.itens.map((i) => i.id)])).toEqual([
      ['Obra', [2]],
      ['Atas', [1, 3]],
    ])
  })
})

describe('busca', () => {
  const itens = [
    doc(1, { titulo: 'Convenção do condomínio', categoria: 'convencao' }),
    doc(2, { titulo: 'Cronograma da obra', categoria: 'obra' }),
    doc(3, { titulo: 'Ata da reunião de outubro', categoria: 'ata' }),
  ]

  it('sem acento e sem maiúscula, no título ou no assunto', () => {
    expect(filtrar(itens, 'CONVENCAO').map((i) => i.id)).toEqual([1])
    expect(filtrar(itens, 'atas').map((i) => i.id)).toEqual([3])
    expect(filtrar(itens, 'reuniao').map((i) => i.id)).toEqual([3])
  })

  it('cada palavra em qualquer ordem; vazio mostra tudo', () => {
    expect(filtrar(itens, 'obra cronograma').map((i) => i.id)).toEqual([2])
    expect(filtrar(itens, '  ').map((i) => i.id)).toEqual([1, 2, 3])
    expect(filtrar(itens, 'piscina')).toEqual([])
  })
})

describe('textos', () => {
  it('data do documento por extenso, sem mudar de dia pelo fuso', () => {
    expect(dataDoDocumento('2026-10-01')).toBe('1 de outubro de 2026')
    expect(dataDoDocumento('2023-12-31')).toBe('31 de dezembro de 2023')
  })

  it('tamanho do arquivo como se fala', () => {
    expect(tamanhoEmTexto(212)).toBe('1 KB')
    expect(tamanhoEmTexto(340 * 1024)).toBe('340 KB')
    expect(tamanhoEmTexto(2.4 * 1024 * 1024)).toBe('2,4 MB')
    expect(tamanhoEmTexto(20 * 1024 * 1024)).toBe('20 MB')
  })

  it('tipo do arquivo', () => {
    expect(tipoEmTexto('application/pdf')).toBe('PDF')
    expect(tipoEmTexto('image/jpeg')).toBe('Foto')
    expect(tipoEmTexto('image/webp')).toBe('Foto')
  })

  it('hoje no horário de Recife, como AAAA-MM-DD', () => {
    // 02:30 em UTC ainda é o dia anterior em Recife (UTC−3).
    expect(hojeEmRecife(new Date('2026-10-13T02:30:00Z'))).toBe('2026-10-12')
  })
})
