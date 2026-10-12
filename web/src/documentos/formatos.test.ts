// Épico A do M3 · formatos dos documentos na voz do morador.
import { describe, expect, it } from 'vitest'
import {
  ASSUNTOS,
  agrupar,
  dataDoDocumento,
  filtrar,
  avisoDaVersao,
  avisoDoDocumentoNovo,
  hojeEmRecife,
  problemaAoEscolher,
  tamanhoEmTexto,
  tipoEmTexto,
} from './formatos'
import type { DocumentoResumo } from './tipos'

// Os mesmos textos que a API grava (api/testes/test_documentos_revisao.py): a prévia mostra o
// aviso como ele vai sair.
describe('prévia do aviso automático (U3, U13)', () => {
  it('documento novo, com a linha da gestão e a categoria que combina', () => {
    expect(avisoDoDocumentoNovo('Regimento interno', 'regimento', ' Leiam até sexta. ')).toEqual({
      titulo: 'Documento novo: Regimento interno',
      categoria: 'Geral',
      texto:
        'Um documento novo foi publicado no Portal: “Regimento interno”.\n\n' +
        'Leiam até sexta.\n\n' +
        'Ele fica guardado em Documentos, no menu do Portal, e o botão “Ver o documento”' +
        ' deste aviso leva direto a ele.',
    })
    expect(avisoDoDocumentoNovo('Cronograma', 'obra', '').categoria).toBe('Obra')
    expect(avisoDoDocumentoNovo('Ata', 'ata', '').categoria).toBe('Reunião')
    expect(avisoDoDocumentoNovo('x'.repeat(120), 'outro', '').titulo).toHaveLength(120)
  })

  it('versão nova (o link do documento a API acrescenta, se souber o endereço)', () => {
    expect(avisoDaVersao('Regimento', 'regimento', 2, '')).toEqual({
      titulo: 'Documento atualizado: Regimento',
      categoria: 'Geral',
      texto:
        'Saiu a versão 2 de um documento do Portal: “Regimento”.\n\n' +
        'Ela fica guardada em Documentos, no menu do Portal.',
    })
  })
})

describe('arquivo na hora de escolher (U10)', () => {
  const arquivo = (type: string, size: number, name = 'a') => ({ type, size, name })

  it('aceita PDF e foto dentro do limite', () => {
    expect(problemaAoEscolher(arquivo('application/pdf', 1000))).toBeNull()
    // Foto grande é reduzida antes de enviar: o tamanho dela é conferido depois.
    expect(problemaAoEscolher(arquivo('image/jpeg', 30 * 1024 * 1024))).toBeNull()
  })

  it('Word, planilha e outros: diz o que fazer', () => {
    expect(problemaAoEscolher(arquivo('application/msword', 10, 'ata.doc'))).toMatch(
      /^Arquivo do Word: salve como PDF/,
    )
    expect(problemaAoEscolher(arquivo('', 10, 'ata.DOCX'))).toMatch(/^Arquivo do Word/)
    expect(problemaAoEscolher(arquivo('application/zip', 10, 'x.zip'))).toMatch(
      /^O Portal aceita PDF e fotos/,
    )
  })

  it('PDF grande demais: o tamanho e como reduzir', () => {
    expect(problemaAoEscolher(arquivo('application/pdf', 25 * 1024 * 1024))).toMatch(
      /^Este PDF tem 25 MB e o limite é 20 MB\. Para reduzir/,
    )
  })

  it('arquivo vazio', () => {
    expect(problemaAoEscolher(arquivo('application/pdf', 0))).toBe(
      'O arquivo está vazio. Escolha outro.',
    )
  })
})

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

  it('tamanho do arquivo como se fala, sem quebrar o número da unidade', () => {
    expect(tamanhoEmTexto(212)).toBe('1\u00a0KB')
    expect(tamanhoEmTexto(340 * 1024)).toBe('340\u00a0KB')
    expect(tamanhoEmTexto(2.4 * 1024 * 1024)).toBe('2,4\u00a0MB')
    expect(tamanhoEmTexto(20 * 1024 * 1024)).toBe('20\u00a0MB')
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
