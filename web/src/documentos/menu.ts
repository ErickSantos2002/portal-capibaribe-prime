// Épico A do M3 · o item "Documentos" do menu (spec do M3, seção 7). Pertence ao épico A.
// Chamado por `casca/menu.ts`, logo depois de "Avisos". Toda unidade vê documentos (H-18); o que
// cada uma vê na lista quem decide é a API.
import type { Eu } from '../api/tipos'
import type { Item } from '../casca/menu'

export function itemDocumentos(eu: Eu): Item | null {
  void eu
  return { para: '/documentos', icone: 'documentos', texto: 'Documentos' }
}
