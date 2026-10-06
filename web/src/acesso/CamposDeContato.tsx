// Responsável, celular e e-mail opcional (RF-04, RNF-10): os mesmos campos no primeiro acesso e
// em "Mudar meus dados".
import { Campo } from './Campo'
import type { ContatoDigitado } from './campos'

interface Props {
  /** Prefixo dos `id` (dois formulários na mesma tela não podem repetir `id`). */
  prefixo: string
  contato: ContatoDigitado
  aoMudar: (contato: ContatoDigitado) => void
  /** Campo com erro (`responsavel_nome`, `celular`, `email`) e a mensagem. */
  erro?: { campo: string | null; mensagem: string } | null
}

export function CamposDeContato({ prefixo, contato, aoMudar, erro }: Props) {
  const erroDe = (campo: string) => (erro?.campo === campo ? erro.mensagem : undefined)
  return (
    <>
      <Campo
        id={`${prefixo}-responsavel_nome`}
        rotulo="Nome de quem responde pela unidade"
        type="text"
        autoComplete="name"
        maxLength={100}
        valor={contato.responsavel_nome}
        aoMudar={(valor) => aoMudar({ ...contato, responsavel_nome: valor })}
        erro={erroDe('responsavel_nome')}
      />
      <Campo
        id={`${prefixo}-celular`}
        rotulo="Celular"
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        valor={contato.celular}
        aoMudar={(valor) => aoMudar({ ...contato, celular: valor })}
        ajuda="Com DDD, como (81) 9 1234-5678. É visto só pela Comissão e pela administração do Portal, para falarem com o apartamento quando precisar."
        erro={erroDe('celular')}
      />
      <Campo
        id={`${prefixo}-email`}
        rotulo="E-mail (opcional)"
        type="email"
        autoComplete="email"
        valor={contato.email}
        aoMudar={(valor) => aoMudar({ ...contato, email: valor })}
        ajuda="Pode deixar em branco. Com e-mail, você vai poder recuperar a senha sozinho."
        erro={erroDe('email')}
      />
    </>
  )
}
