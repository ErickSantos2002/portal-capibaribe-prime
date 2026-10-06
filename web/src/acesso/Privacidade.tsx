// Política de privacidade (RNF-10, RNF-11, RNF-12). Pública: visível antes do primeiro acesso.
// Fonte: docs/04-modelo-de-dados.md, seção 5 (inventário dos dados pessoais da E1). Mudou o
// inventário, muda este texto.
//
// Decisões do Erick em 06/10/2026 (duvidas-m1.md, "Fim do marco"): a Comissão vê os contatos
// (A6); o responsável é o Erick, em nome da Comissão, sem unidade, bloco, endereço nem CPF dele,
// porque o repositório é público (A7). Os pedidos vão pelo grupo ou pela Comissão até o Portal
// ter e-mail próprio, no M2 (ADR-0006); aí o e-mail entra em "Seus direitos".
import { Tela } from '../casca/Tela'
import './acesso.css'

const DADOS = [
  {
    dado: 'Nome de quem responde pela unidade',
    para: 'saber com quem falar sobre o apartamento.',
  },
  {
    dado: 'Celular',
    para: 'a Comissão e a administração falarem com a unidade, e confirmar quem é o dono se a conta for usada por outra pessoa.',
  },
  {
    dado: 'E-mail (opcional)',
    para: 'recuperar a senha sozinho e receber os avisos também por e-mail, quando essas funções chegarem ao Portal. Sem e-mail, tudo funciona do mesmo jeito.',
  },
  {
    dado: 'Aparelho conectado (só o tipo, como “Android · Chrome”)',
    para: 'você reconhecer os aparelhos que entraram com a conta do apartamento e desconectar algum.',
  },
]

/** O texto da política, usado na página própria e dobrado dentro do primeiro acesso. */
export function TextoDaPolitica() {
  return (
    <div className="politica">
      <h2>O que guardamos e para quê</h2>
      <p>A conta é do apartamento, não de uma pessoa. Sobre quem responde por ele, guardamos só:</p>
      <dl>
        {DADOS.map(({ dado, para }) => (
          <div className="dado" key={dado}>
            <dt>{dado}</dt>
            <dd>Para quê: {para}</dd>
          </div>
        ))}
      </dl>

      <h2>Quem vê</h2>
      <p>
        Nome, celular e e-mail são vistos só pelo próprio apartamento, pela Comissão e pela
        administração do Portal. Os aparelhos conectados, só o próprio apartamento vê. Outros
        moradores não veem os dados de ninguém.
      </p>

      <h2>Quem cuida dos dados</h2>
      <p>
        O responsável pelos dados é Erick Santos, morador que mantém o Portal, em nome da Comissão
        dos compradores do Capibaribe Prime.
      </p>

      <h2>Onde os dados ficam</h2>
      <p>
        Num banco de dados da Neon, e o Portal funciona na Vercel. As duas empresas guardam tudo em
        servidores em São Paulo.
      </p>

      <h2>O que não guardamos</h2>
      <ul>
        <li>CPF, RG, contrato de compra ou renda.</li>
        <li>
          Endereço de internet (IP) ou localização. A única exceção: quando alguém erra a senha,
          guardamos por 15 minutos um código feito a partir do IP (não o IP em si), só para
          bloquear quem tenta adivinhar a senha.
        </li>
        <li>Nenhum rastreador nem propaganda. O único cookie é o que mantém você conectado.</li>
      </ul>

      <h2>Por quanto tempo</h2>
      <p>
        Até você apagar os dados, ou até a administração voltar a conta do apartamento para a senha
        inicial. O registro de ações do Portal (por exemplo, “o apartamento entrou pela primeira
        vez”) fica guardado, mas sem nome, celular nem e-mail.
      </p>

      <h2>Seus direitos</h2>
      <p>
        Em <b>Minha unidade</b> você vê tudo o que está guardado, corrige o que quiser e, em{' '}
        <b>Apagar meus dados</b>, apaga nome, celular e e-mail. A conta do apartamento continua
        existindo e volta para a senha inicial.
      </p>
      <p>
        Para qualquer outro pedido sobre os seus dados (ver, corrigir ou apagar) ou para tirar
        dúvidas, escreva no grupo de WhatsApp dos compradores ou fale com alguém da Comissão.
      </p>
    </div>
  )
}

export function Privacidade() {
  return (
    <Tela titulo="Política de privacidade" voltar="/entrar">
      <TextoDaPolitica />
    </Tela>
  )
}
