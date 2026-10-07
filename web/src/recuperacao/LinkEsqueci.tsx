// Épico B do M2 · o "Esqueci minha senha" da tela de entrada (spec do M2, seção 7): link para a
// tela que pede o link de senha nova por e-mail (H-04).
import { Link } from 'react-router'
import './recuperacao.css'

export function LinkEsqueci() {
  return (
    <p className="centro recuperacao-link">
      <Link className="texto-link" to="/esqueci-a-senha">
        Esqueci minha senha
      </Link>
    </p>
  )
}
