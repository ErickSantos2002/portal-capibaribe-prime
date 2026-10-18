// Indicações · os endereços das telas (spec, seção 3).
export const CAMINHO_INDICACOES = '/indicacoes'
export const CAMINHO_NOVA_INDICACAO = '/indicacoes/nova'
export const CAMINHO_CATEGORIAS = '/indicacoes/categorias'

/** O prestador aberto; `opinar` abre direto o formulário da opinião (`?opinar=1`). */
export function caminhoIndicacao(id: number, opinar = false): string {
  return `/indicacoes/${id}${opinar ? '?opinar=1' : ''}`
}
