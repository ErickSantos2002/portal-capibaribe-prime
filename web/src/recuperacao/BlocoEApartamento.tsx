// Bloco em 5 botões e apartamento num campo à parte, igual à tela de entrar (Entrar.tsx): quem
// pede o link escreve a unidade do mesmo jeito que escreve para entrar. As regras de limpar e
// colar são as mesmas (`limparApartamento` de acesso/campos.ts).
import type { ClipboardEvent } from 'react'
import { limparApartamento } from '../acesso/campos'

const BLOCOS = ['1', '2', '3', '4', '5']

interface Props {
  bloco: string
  apartamento: string
  aoMudarBloco: (bloco: string) => void
  aoMudarApartamento: (apartamento: string) => void
}

export function BlocoEApartamento({
  bloco,
  apartamento,
  aoMudarBloco,
  aoMudarApartamento,
}: Props) {
  function aoColar(evento: ClipboardEvent<HTMLInputElement>) {
    const { apartamento: limpo, bloco: doLogin } = limparApartamento(
      evento.clipboardData.getData('text'),
      true,
    )
    if (doLogin) {
      evento.preventDefault()
      aoMudarBloco(doLogin)
      aoMudarApartamento(limpo)
    }
  }

  return (
    <>
      <fieldset className="blocos">
        <legend>Bloco</legend>
        <div className="blocos-op">
          {BLOCOS.map((numero) => (
            <label key={numero}>
              <input
                type="radio"
                name="bloco"
                value={numero}
                checked={bloco === numero}
                onChange={() => aoMudarBloco(numero)}
                aria-label={`Bloco ${numero}`}
              />
              <span aria-hidden="true">{numero}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <label htmlFor="apartamento">Apartamento</label>
      <input
        id="apartamento"
        className="apto"
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={apartamento}
        onChange={(e) => aoMudarApartamento(limparApartamento(e.target.value, false).apartamento)}
        onPaste={aoColar}
        aria-describedby="ajuda-apartamento"
      />
      <p className="ajuda" id="ajuda-apartamento">
        O número da porta, como 101. No térreo, 007 ou só 7.
      </p>
    </>
  )
}
