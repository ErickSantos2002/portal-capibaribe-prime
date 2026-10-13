// Épico B do M4 · o botão "Ir para a enquete" no aviso automático (H-13; spec do M4, seção 4).
// Pertence ao épico B. Chamado por `avisos/AvisoAberto.tsx`, depois do botão do documento. Hoje
// não mostra nada.
import type { EnqueteDoAviso as Enquete } from '../../avisos/tipos'

export function EnqueteDoAviso({ enquete }: { enquete: Enquete | null }) {
  void enquete
  return null
}
