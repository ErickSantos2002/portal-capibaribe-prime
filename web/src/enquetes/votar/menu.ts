// Épico B do M4 · o item "Enquetes" do menu (spec do M4, seção 4). Pertence ao épico B.
// Chamado por `casca/menu.ts`, logo depois de "Avisos". Hoje `null`: sem item no menu até o
// épico B ter a tela.
import type { Eu } from '../../api/tipos'
import type { Item } from '../../casca/menu'

export function itemEnquetes(eu: Eu): Item | null {
  void eu
  return null
}
