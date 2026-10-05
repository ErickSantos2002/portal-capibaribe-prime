// Campo de formulário com rótulo, ajuda e erro ligados por aria-describedby (WCAG 3.3.1).
import type { InputHTMLAttributes } from 'react'

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'onChange'> {
  id: string
  rotulo: string
  valor: string
  aoMudar: (valor: string) => void
  ajuda?: string
  /** Mensagem de erro deste campo (borda vermelha + texto abaixo). */
  erro?: string
}

export function Campo({ id, rotulo, valor, aoMudar, ajuda, erro, ...resto }: Props) {
  const descricao = [ajuda && `${id}-ajuda`, erro && `${id}-erro`].filter(Boolean).join(' ')
  return (
    <>
      <label htmlFor={id}>{rotulo}</label>
      <input
        id={id}
        value={valor}
        onChange={(e) => aoMudar(e.target.value)}
        className={erro ? 'campo-erro' : undefined}
        aria-invalid={erro ? true : undefined}
        aria-describedby={descricao || undefined}
        {...resto}
      />
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
