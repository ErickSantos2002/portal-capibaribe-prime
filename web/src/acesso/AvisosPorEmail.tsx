// Ajustes do M2 · "Receber os avisos por e-mail", na seção Notificações de Minha unidade
// (resposta do Erick ao item 7 de duvidas-m2.md). Vem marcada; desmarcar para as cópias dos
// avisos, mas o e-mail continua cadastrado para o "Esqueci minha senha". Salva na hora, como o
// botão das notificações deste aparelho; vale para o apartamento inteiro (revisão dos ajustes).
import { useState } from 'react'
import { useRecado } from '../casca/contextoRecado'
import { mudarAvisosPorEmail } from './api'
import { CaixaDeErro } from './CaixaDeErro'
import { erroDaFalha } from './campos'
import type { MinhaUnidade } from './tipos'

// Hífen que não quebra (U+2011): "e‑mail" nunca vira "e-" no fim da linha.
const EMAIL = 'e\u2011mail'

interface Props {
  dados: MinhaUnidade
  aoMudar: (novos: MinhaUnidade) => void
}

export function AvisosPorEmail({ dados, aoMudar }: Props) {
  const recado = useRecado()
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<{ mensagem: string; vez: number } | null>(null)

  if (!dados.email) {
    return (
      <div className="folha notif-cartao acesso-email-avisos">
        <p className="ajuda">
          Para receber os avisos por {EMAIL}, cadastre um {EMAIL} em “Mudar meus dados”.
        </p>
      </div>
    )
  }

  async function aoTrocar(receber: boolean) {
    // `aria-disabled` em vez de `disabled`: o foco fica na caixa (revisão dos ajustes, item 4),
    // e o toque durante o salvamento é ignorado aqui.
    if (salvando) return
    setSalvando(true)
    setErro(null)
    try {
      aoMudar(await mudarAvisosPorEmail(receber))
      recado(
        receber
          ? 'Pronto: os avisos voltam a chegar por e-mail.'
          : 'Pronto: os avisos não chegam mais por e-mail.',
      )
    } catch (falha) {
      setErro((anterior) => ({
        mensagem: erroDaFalha(falha).mensagem,
        vez: (anterior?.vez ?? 0) + 1,
      }))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="folha notif-cartao acesso-email-avisos">
      {erro && (
        <CaixaDeErro vez={erro.vez} focar="avisos-por-email">
          <p>{erro.mensagem}</p>
        </CaixaDeErro>
      )}
      <label className="opcao">
        <input
          id="avisos-por-email"
          type="checkbox"
          checked={dados.receber_avisos_email}
          aria-disabled={salvando || undefined}
          aria-describedby="avisos-por-email-ajuda"
          onChange={(evento) => void aoTrocar(evento.target.checked)}
        />
        Receber os avisos por {EMAIL}
      </label>
      <p className="ajuda" id="avisos-por-email-ajuda">
        {salvando ? (
          'Salvando…'
        ) : (
          <>
            Vale para o apartamento inteiro, em qualquer aparelho.{' '}
            {dados.receber_avisos_email
              ? `Cada aviso novo chega também em ${dados.email}.`
              : `Os avisos não chegam em ${dados.email}.`}{' '}
            O {EMAIL} continua cadastrado para o “Esqueci minha senha”.
          </>
        )}
      </p>
    </div>
  )
}
