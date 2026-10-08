// Contrato do M3 no front (docs/superpowers/specs/m3-contrato.md, seções 5 e 7).
import { describe, expect, it } from 'vitest'
import { oQueFez } from './administracao/frases'
import type { ItemHistorico } from './administracao/tipos'

describe('histórico do M3 em frases (H-11)', () => {
  const base: ItemHistorico = {
    id: 1,
    ocorrido_em: '2026-11-02T21:03:00Z',
    unidade: { login: '2304', bloco: 2, apartamento: '304' },
    acao: 'arquivo_recusado',
    entidade: 'arquivo',
    entidade_id: 7,
    unidade_afetada: null,
    aviso_titulo: null,
    detalhes: {
      motivo: 'conteudo',
      finalidade: 'documento',
      tipo_declarado: 'application/pdf',
      tipo_encontrado: null,
      tamanho_bytes: 1000,
    },
  }

  it('arquivo recusado: diz por quê, sem o nome do arquivo', () => {
    expect(oQueFez(base)).toBe('tentou enviar um arquivo que não era PDF nem foto (recusado)')
    expect(oQueFez({ ...base, detalhes: { ...base.detalhes, motivo: 'tamanho' } })).toBe(
      'tentou enviar um arquivo maior que o limite (recusado)',
    )
  })

  it('documentos: publicar, versão nova e arquivar', () => {
    const doc = { ...base, entidade: 'documento', detalhes: {} }
    expect(oQueFez({ ...doc, acao: 'documento_publicado' })).toBe('publicou um documento')
    expect(oQueFez({ ...doc, acao: 'documento_versao_enviada', detalhes: { versao: 3 } })).toBe(
      'enviou a versão 3 de um documento',
    )
    expect(oQueFez({ ...doc, acao: 'documento_versao_enviada' })).toBe(
      'enviou uma versão nova de um documento',
    )
    expect(oQueFez({ ...doc, acao: 'documento_arquivado' })).toBe('arquivou um documento')
  })
})
