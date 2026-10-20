// Classificados · os endereços das telas (spec, seção 3).
export const CAMINHO_CLASSIFICADOS = '/classificados'
export const CAMINHO_NOVO_ANUNCIO = '/classificados/novo'
export const CAMINHO_MEUS_ANUNCIOS = '/classificados/meus'
export const CAMINHO_CATEGORIAS_CLASSIFICADOS = '/classificados/categorias'

export function caminhoAnuncio(id: number): string {
  return `/classificados/${id}`
}

export function caminhoEditarAnuncio(id: number): string {
  return `/classificados/${id}/editar`
}
