// Campo de formulário com rótulo, ajuda e erro ligados por aria-describedby (WCAG 3.3.1).
// Campo de senha ganha o botão "Mostrar"/"Ocultar" (revisão do M1, U3): quem digita devagar,
// no celular, confere o que escreveu antes de errar e gastar uma tentativa.
import { useState, type InputHTMLAttributes } from 'react'

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'onChange'> {
  id: string
  rotulo: string
  valor: string
  aoMudar: (valor: string) => void
  ajuda?: string
  /** Mensagem de erro deste campo (borda vermelha + texto abaixo). */
  erro?: string
}

export function Campo({ id, rotulo, valor, aoMudar, ajuda, erro, type, ...resto }: Props) {
  const [visivel, setVisivel] = useState(false)
  const senha = type === 'password'
  const descricao = [ajuda && `${id}-ajuda`, erro && `${id}-erro`].filter(Boolean).join(' ')
  const campo = (
    <input
      id={id}
      type={senha && visivel ? 'text' : type}
      value={valor}
      onChange={(e) => aoMudar(e.target.value)}
      className={erro ? 'campo-erro' : undefined}
      aria-invalid={erro ? true : undefined}
      aria-describedby={descricao || undefined}
      {...(senha ? { autoCapitalize: 'none', autoCorrect: 'off', spellCheck: false } : {})}
      {...resto}
    />
  )
  return (
    <>
      <label htmlFor={id}>{rotulo}</label>
      {senha ? (
        <div className="campo-senha">
          {campo}
          <button
            type="button"
            className="campo-senha-ver"
            aria-controls={id}
            aria-label={`${visivel ? 'Ocultar' : 'Mostrar'} ${rotulo.toLowerCase()}`}
            onClick={() => setVisivel((v) => !v)}
          >
            {visivel ? 'Ocultar' : 'Mostrar'}
          </button>
        </div>
      ) : (
        campo
      )}
      {erro && (
        <p className="acesso-campo-erro" id={`${id}-erro`}>
          {erro}
        </p>
      )}
      {ajuda && (
        <p className="ajuda" id={`${id}-ajuda`}>
          {ajuda}
        </p>
      )}
    </>
  )
}
