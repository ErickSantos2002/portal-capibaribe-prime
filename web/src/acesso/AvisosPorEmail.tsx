// Ajustes do M2 · "Receber os avisos por e-mail", na seção Notificações de Minha unidade
// (resposta do Erick ao item 7 de duvidas-m2.md). Vem marcada; desmarcar para as cópias dos
// avisos, mas o e-mail continua cadastrado para o "Esqueci minha senha". Salva na hora, como o
// botão das notificações deste aparelho.
import { useState } from 'react'
import { useRecado } from '../casca/contextoRecado'
import { mudarAvisosPorEmail } from './api'
import { CaixaDeErro } from './CaixaDeErro'
import { erroDaFalha } from './campos'
import type { MinhaUnidade } from './tipos'

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
          Para receber os avisos por e-mail, cadastre um e-mail em “Mudar meus dados”.
        </p>
      </div>
    )
  }

  async function aoTrocar(receber: boolean) {
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
          disabled={salvando}
          aria-describedby="avisos-por-email-ajuda"
          onChange={(evento) => void aoTrocar(evento.target.checked)}
        />
        Receber os avisos por e-mail
      </label>
      <p className="ajuda" id="avisos-por-email-ajuda">
        {dados.receber_avisos_email
          ? `Cada aviso novo chega também em ${dados.email}.`
          : `Os avisos não chegam em ${dados.email}.`}{' '}
        O e-mail continua cadastrado para o “Esqueci minha senha”.
      </p>
    </div>
  )
}
