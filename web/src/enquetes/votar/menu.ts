// Épico B do M4 · o item "Enquetes" do menu (spec do M4, seção 4). Pertence ao épico B.
// Chamado por `casca/menu.ts`, logo depois de "Avisos". Toda unidade vota (H-21); quais
// enquetes cada uma vê quem decide é a API.
import type { Eu } from '../../api/tipos'
import type { Lugar } from '../../casca/menu'
import { CAMINHO_ENQUETES } from '../caminhos'

export function itemEnquetes(eu: Eu): Lugar | null {
  void eu
  return {
    para: CAMINHO_ENQUETES,
    icone: 'enquetes',
    texto: 'Enquetes',
    frase: 'Vote pela sua unidade',
    grupo: 'dia-a-dia',
    naBarra: 2,
  }
}
