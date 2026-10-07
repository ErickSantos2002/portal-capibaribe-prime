// "Esqueci minha senha" (H-04; protótipo #esqueci): pede só o bloco e o apartamento. A resposta
// é sempre a mesma (a API não revela se a unidade tem e-mail), e quem não tem e-mail fica
// sabendo o que fazer.
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { CaixaDeErro } from '../acesso/CaixaDeErro'
import { erroDaFalha, montarLogin } from '../acesso/campos'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { pedirRecuperacao } from './api'
import { BlocoEApartamento } from './BlocoEApartamento'
import '../acesso/acesso.css'
import './recuperacao.css'

// O mesmo formato que a API aceita (RF-03): bloco 1 a 9, andar 0 a 7, dois dígitos.
const LOGIN_POSSIVEL = /^[1-9][0-7][0-9]{2}$/

interface Erro {
  mensagem: string
  campo?: string
  vez: number
}

export function EsqueciASenha() {
  const [bloco, setBloco] = useState('')
  const [apartamento, setApartamento] = useState('')
  const [erro, setErro] = useState<Erro | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [resposta, setResposta] = useState<string | null>(null)

  function mostrarErro(mensagem: string, campo?: string) {
    setErro((anterior) => ({ mensagem, campo, vez: (anterior?.vez ?? 0) + 1 }))
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const login = montarLogin(bloco, apartamento)
    if (!bloco) return mostrarErro('Escolha o bloco nos botões de 1 a 5.')
    if (!login) return mostrarErro('Escreva o número do apartamento, como 101.', 'apartamento')
    if (!LOGIN_POSSIVEL.test(login)) {
      return mostrarErro(
        'Esse apartamento não existe. Confira o bloco e o número da porta.',
        'apartamento',
      )
    }
    setEnviando(true)
    try {
      const { mensagem } = await pedirRecuperacao(login)
      setResposta(mensagem)
    } catch (falha) {
      mostrarErro(erroDaFalha(falha).mensagem)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Tela titulo="Esqueci minha senha" voltar="/entrar">
      {resposta ? (
        <>
          <div className="aviso-caixa info" role="status">
            <Icone nome="info" />
            <p>{resposta}</p>
          </div>
          <p>
            O link vale por 1 hora. Sem e-mail cadastrado, fale com a administração do Portal no
            grupo do WhatsApp. Ela volta sua senha para a inicial.
          </p>
          <Link className="botao leve" to="/entrar">
            Voltar para a entrada
          </Link>
        </>
      ) : (
        <>
          <p>
            Escreva o bloco e o apartamento. Se houver e-mail cadastrado, mandamos um link para
            criar uma senha nova.
          </p>
          {erro && (
            <CaixaDeErro vez={erro.vez} focar={erro.campo}>
              <p>{erro.mensagem}</p>
            </CaixaDeErro>
          )}
          <form onSubmit={aoEnviar} noValidate>
            <BlocoEApartamento
              bloco={bloco}
              apartamento={apartamento}
              aoMudarBloco={setBloco}
              aoMudarApartamento={setApartamento}
            />
            <button className="botao acesso-enviar" type="submit" disabled={enviando}>
              {enviando ? 'Mandando…' : 'Mandar link'}
            </button>
          </form>
          <p className="ajuda recuperacao-sem-email">
            Não cadastrou e-mail? Fale com a administração do Portal no grupo do WhatsApp. Ela
            volta sua senha para a inicial.
          </p>
        </>
      )}
    </Tela>
  )
}
