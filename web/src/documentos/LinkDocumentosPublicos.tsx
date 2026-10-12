// Épico A do M3 · o link "Ver documentos públicos" da tela de entrada (H-18: os públicos
// aparecem até para quem não entrou). Pertence ao épico A. Encaixado em `acesso/Entrar.tsx`,
// depois do "Esqueci minha senha".
import { Link } from 'react-router'
import { Icone } from '../casca/Icone'

export function LinkDocumentosPublicos() {
  return (
    <p className="centro">
      <Link className="texto-link com-icone" to="/documentos/publicos">
        <Icone nome="documentos" tamanho={20} /> Ver documentos públicos
      </Link>
    </p>
  )
}
