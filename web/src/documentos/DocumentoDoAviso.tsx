// Épico A do M3 · o botão "Abrir o documento" do aviso automático (RF-33; spec do M3, seção 7).
// Pertence ao épico A. Já encaixado em `avisos/AvisoAberto.tsx`, depois do texto do aviso; não
// mostra nada até o épico.
import type { DocumentoDoAviso as Dados } from '../avisos/tipos'

export function DocumentoDoAviso({ documento }: { documento: Dados | null }) {
  void documento
  return null
}
