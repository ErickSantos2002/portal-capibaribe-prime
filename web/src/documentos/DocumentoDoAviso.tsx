// Épico A do M3 · o botão "Abrir o documento" do aviso automático (RF-33; spec do M3, seção 7).
// Pertence ao épico A. Encaixado em `avisos/AvisoAberto.tsx`, depois do texto do aviso. A API só
// manda o `documento` se a unidade pode vê-lo e ele não está arquivado.
import { Link } from 'react-router'
import type { DocumentoDoAviso as Dados } from '../avisos/tipos'
import { Icone } from '../casca/Icone'
import './documentos.css'

export function DocumentoDoAviso({ documento }: { documento: Dados | null }) {
  if (!documento) return null
  return (
    <Link className="doc-do-aviso" to={`/documentos/${documento.id}`}>
      <Icone nome="documentos" tamanho={32} />
      <span>
        <b>Abrir o documento</b>
        <span className="doc-do-aviso-titulo">{documento.titulo}</span>
      </span>
      <Icone nome="seta" />
    </Link>
  )
}
