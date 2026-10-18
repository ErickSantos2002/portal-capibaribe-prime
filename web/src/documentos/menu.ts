// Épico A do M3 · o item "Documentos" do menu (spec do M3, seção 7). Pertence ao épico A.
// Chamado por `casca/menu.ts`, logo depois de "Avisos". Toda unidade vê documentos (H-18); o que
// cada uma vê na lista quem decide é a API.
import type { Eu } from '../api/tipos'
import type { Lugar } from '../casca/menu'

export function itemDocumentos(eu: Eu): Lugar | null {
  void eu
  return {
    para: '/documentos',
    icone: 'documentos',
    texto: 'Documentos',
    curto: 'Docs',
    frase: 'Memorial, atas e contratos',
    grupo: 'dia-a-dia',
    naBarra: 3,
  }
}
