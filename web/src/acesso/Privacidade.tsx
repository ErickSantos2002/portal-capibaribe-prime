// Política de privacidade (RNF-10, RNF-11, RNF-12). Pública: visível antes do primeiro acesso.
// Fonte: docs/04-modelo-de-dados.md, seção 5 (inventário dos dados pessoais da E1). Mudou o
// inventário, muda este texto.
import { Tela } from '../casca/Tela'
import './acesso.css'

const DADOS = [
  {
    dado: 'Nome de quem responde pela unidade',
    para: 'saber com quem falar sobre o apartamento.',
  },
  {
    dado: 'Celular',
    para: 'a administração falar com a unidade e confirmar quem é o dono se a conta for usada por outra pessoa.',
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
        O próprio apartamento e a administração do Portal. Outros moradores não veem nome, celular
        nem e-mail de ninguém.
      </p>

      <h2>O que não guardamos</h2>
      <ul>
        <li>CPF, RG, contrato de compra ou renda.</li>
        <li>Endereço de internet (IP) ou localização.</li>
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
        existindo e volta para a senha inicial. Dúvidas: fale com a administração do Portal no grupo
        do WhatsApp.
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
