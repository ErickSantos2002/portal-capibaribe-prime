// M3 · Épico B: ícones dos anexos que o `Icone` da casca não tem (dúvida 2 do épico B). Mesmo
// traço (2 px, 24×24), sempre ao lado de texto, por isso decorativos (aria-hidden).
// M5: o `tamanho` é px de desenho (24 = com a letra de fábrica) e vira rem: cresce com a letra.
import { tamanhoDoIcone } from '../casca/emRem'

export type NomeDoIconeAnexo = 'clipe' | 'foto' | 'fechar'

function Desenho({ nome }: { nome: NomeDoIconeAnexo }) {
  switch (nome) {
    case 'clipe':
      return (
        <path d="M20.5 11.5l-8.2 8.2a5 5 0 0 1-7-7l8.6-8.6a3.4 3.4 0 0 1 4.8 4.8l-8.6 8.6a1.8 1.8 0 0 1-2.5-2.5L15.5 7" />
      )
    case 'foto':
      return (
        <>
          <rect x="3" y="4.5" width="18" height="15" rx="2" />
          <circle cx="9" cy="10" r="2" />
          <path d="M21 16l-5-5-9 8.5" />
        </>
      )
    default:
      return <path d="M6 6l12 12M18 6 6 18" />
  }
}

export function IconeAnexo({ nome, tamanho = 24 }: { nome: NomeDoIconeAnexo; tamanho?: number }) {
  return (
    <svg
      {...tamanhoDoIcone(tamanho)}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <Desenho nome={nome} />
    </svg>
  )
}
