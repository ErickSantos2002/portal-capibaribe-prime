import { Icone } from './Icone'
import { useTema } from './tema'

/** O botão mostra para onde vai: no claro, a lua (escurecer); no escuro, o sol (clarear). */
export function BotaoTema({ solto }: { solto?: boolean }) {
  const [tema, alternar] = useTema()
  const escuro = tema === 'escuro'
  return (
    <button type="button" className={solto ? 'tema-btn solto' : 'tema-btn'} onClick={alternar}>
      <Icone
        nome={escuro ? 'sol' : 'lua'}
        rotulo={escuro ? 'Usar tema claro' : 'Usar tema escuro'}
      />
    </button>
  )
}
