// Celular e e-mail para ler (M5, revisões, U6): com a letra grande, o "(81) 9 0000-0003" partia
// no hífen ("0000-" / "0003") e o e-mail cortava em qualquer letra ("example.co" / "m", já com a
// letra de fábrica). O número fica preso numa linha (só o DDD pode ficar na de cima); o e-mail
// ganha pontos de quebra (<wbr>) depois do @ e antes de cada ponto, onde a quebra se lê.
import { Fragment } from 'react'
import { formatarCelular } from './formatar'

export function Celular({ digitos }: { digitos: string }) {
  const texto = formatarCelular(digitos)
  const ddd = /^(\(\d{2}\)) (.+)$/.exec(texto)
  if (!ddd) return <>{texto}</>
  return (
    <>
      {ddd[1]} <span className="fone-numero">{ddd[2]}</span>
    </>
  )
}

export function Email({ endereco }: { endereco: string }) {
  // "a.b@c.com" → "a", ".b@", "c", ".com": quebra depois do @ e antes de cada ponto.
  const partes = endereco.split(/(?=\.)|(?<=@)/)
  return (
    <span className="email">
      {partes.map((parte, i) => (
        <Fragment key={i}>
          {i > 0 && <wbr />}
          {parte}
        </Fragment>
      ))}
    </span>
  )
}
