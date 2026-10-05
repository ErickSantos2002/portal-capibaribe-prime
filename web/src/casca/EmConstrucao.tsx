// Marcação de lugar das telas do M1 (onda 1): cada épico troca pela tela de verdade.
import { Tela } from './Tela'

interface Props {
  titulo: string
  /** História e épico, ex.: "H-14 · épico C". */
  historia: string
  voltar?: string
  entrada?: boolean
}

export function EmConstrucao({ titulo, historia, voltar, entrada }: Props) {
  return (
    <Tela titulo={titulo} voltar={voltar} entrada={entrada}>
      {entrada && (
        <div className="entrada">
          <h1 className="titulo">{titulo}</h1>
        </div>
      )}
      <div className="folha em-construcao">
        <p className="vazio">Tela em construção ({historia}).</p>
      </div>
    </Tela>
  )
}
