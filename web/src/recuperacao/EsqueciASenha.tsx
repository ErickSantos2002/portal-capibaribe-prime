// "Esqueci minha senha" (H-04; protótipo #esqueci): pede só o bloco e o apartamento. A resposta
// é sempre a mesma (a API não revela se a unidade tem e-mail), e quem não tem e-mail fica
// sabendo o que fazer.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { CaixaDeErro } from '../acesso/CaixaDeErro'
import { erroDaFalha, montarLogin } from '../acesso/campos'
import type { UnidadeRef } from '../api/tipos'
import { Icone } from '../casca/Icone'
import { Tela } from '../casca/Tela'
import { pedirRecuperacao } from './api'
import { BlocoEApartamento } from './BlocoEApartamento'
import type { RecuperacaoPedida } from './tipos'
import '../acesso/acesso.css'
import './recuperacao.css'

// A planta do prédio (a mesma regra do protótipo, `UNIDADE_OK`): blocos 1 a 5, andares 0
// (térreo) a 7, apartamentos 01 a 08. A planta é pública: dizer que um apartamento não existe
// não revela nada de ninguém.
const UNIDADE_QUE_EXISTE = /^[1-5][0-7]0[1-8]$/
// Como na tela de entrar: "a senha que a Comissão mandou no grupo" (não "a senha inicial").
const ELA_VOLTA_A_SENHA =
  'Ela volta a senha do apartamento para a senha que a Comissão mandou no grupo.'

interface Erro {
  mensagem: string
  campo?: string
  vez: number
}

interface Pedido {
  resposta: RecuperacaoPedida
  unidade: UnidadeRef
}

function PedidoFeito({ pedido }: { pedido: Pedido }) {
  const caixa = useRef<HTMLDivElement>(null)
  // O foco vai para o resultado: o leitor de tela lê na hora, e quem usa teclado não fica
  // num botão que sumiu.
  useEffect(() => caixa.current?.focus(), [])
  const { resposta, unidade } = pedido
  return (
    <>
      <div ref={caixa} className="aviso-caixa info" role="status" tabIndex={-1}>
        <Icone nome="info" />
        <p>{resposta.mensagem}</p>
      </div>
      <p>
        Pedido feito para o{' '}
        <b>
          Bloco {unidade.bloco}, apartamento {unidade.apartamento}
        </b>
        . O e-mail chega em alguns minutos, de <b>Portal Capibaribe Prime</b>
        {resposta.remetente ? ` (${resposta.remetente})` : ''}
        {`, com o assunto “${resposta.assunto}”. `}
        Se não aparecer, olhe também em Spam ou Lixo eletrônico. O link vale por 1 hora.
      </p>
      <p>
        Sem e-mail cadastrado, fale com a administração do Portal no grupo do WhatsApp.{' '}
        {ELA_VOLTA_A_SENHA}
      </p>
      <Link className="botao leve" to="/entrar">
        Voltar para a entrada
      </Link>
    </>
  )
}

export function EsqueciASenha() {
  const [bloco, setBloco] = useState('')
  const [apartamento, setApartamento] = useState('')
  const [erro, setErro] = useState<Erro | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [pedido, setPedido] = useState<Pedido | null>(null)

  function mostrarErro(mensagem: string, campo?: string) {
    setErro((anterior) => ({ mensagem, campo, vez: (anterior?.vez ?? 0) + 1 }))
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault()
    const login = montarLogin(bloco, apartamento)
    if (!bloco) return mostrarErro('Escolha o bloco nos botões de 1 a 5.')
    if (!login) return mostrarErro('Escreva o número do apartamento, como 101.', 'apartamento')
    if (!UNIDADE_QUE_EXISTE.test(login)) {
      return mostrarErro(
        'Esse apartamento não existe. Confira o bloco e o número da porta.',
        'apartamento',
      )
    }
    setEnviando(true)
    try {
      const resposta = await pedirRecuperacao(login)
      setPedido({
        resposta,
        unidade: { login, bloco: Number(login[0]), apartamento: login.slice(1) },
      })
    } catch (falha) {
      mostrarErro(erroDaFalha(falha).mensagem)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Tela titulo="Esqueci minha senha" voltar="/entrar">
      {pedido ? (
        <PedidoFeito pedido={pedido} />
      ) : (
        <>
          <p>
            Escreva o bloco e o apartamento. Se houver e-mail cadastrado, enviamos um link para
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
              {enviando ? 'Enviando…' : 'Enviar link'}
            </button>
          </form>
          <p className="ajuda recuperacao-sem-email">
            Não cadastrou e-mail? Fale com a administração do Portal no grupo do WhatsApp.{' '}
            {ELA_VOLTA_A_SENHA}
          </p>
        </>
      )}
    </Tela>
  )
}
