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
      <p>
        Em <b>Indicações</b>, guardamos também o que os moradores escrevem: o nome e o telefone (e,
        se alguém informar, o Instagram) do prestador de serviço indicado, para os vizinhos falarem
        com ele, e a sua opinião sobre ele (se recomenda e o que você contou), para ajudar os
        vizinhos a escolher.
      </p>
      <p>
        Em <b>Classificados</b>, guardamos o anúncio que o apartamento publica (o que é, a
        descrição, o preço e até 4 fotos) e o WhatsApp ou telefone que você escolher para aquele
        anúncio, para os vizinhos falarem com você. As fotos ficam guardadas na Cloudflare, a
        empresa que guarda os documentos do Portal.
      </p>

      <h2>Quem vê</h2>
      <p>
        Nome, celular e e-mail são vistos só pelo próprio apartamento, pela Comissão e pela
        administração do Portal. Os aparelhos conectados, só o próprio apartamento vê. Outros
        moradores não veem os dados de ninguém.
      </p>
      <p>
        Nas Indicações, a sua opinião aparece com o bloco e o apartamento para quem entra no Portal,
        nunca com o seu nome. O aviso “Tem algo errado aqui?” só a Comissão e a administração veem,
        sem saber de qual apartamento veio.
      </p>
      <p>
        Nos Classificados, o anúncio aparece com o bloco e o apartamento e com o contato que você
        escolheu, só para quem entra no Portal, nunca com o seu nome. As fotos também aparecem para
        todos os vizinhos: evite pessoas e documentos nelas. A localização (GPS) que a foto do
        celular costuma trazer é apagada antes do envio.
      </p>

      <h2>Quem cuida dos dados</h2>
      <p>
        O responsável pelos dados é Erick Santos, morador que mantém o Portal, em nome da Comissão
        dos compradores do Capibaribe Prime.
      </p>

      <h2>Onde os dados ficam</h2>
      <p>
        Os dados ficam num banco de dados (Postgres) da empresa Neon, e o Portal funciona na
        Vercel. As duas usam servidores em São Paulo.
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
      <p>
        Os anúncios dos Classificados duram pouco, sem ninguém precisar apagar: o encerrado é
        apagado de vez em 7 dias e o vencido, em 30, com as fotos. As fotos não entram na cópia de
        segurança do Portal.
      </p>

      <h2>Seus direitos</h2>
      <p>
        Em <b>Minha unidade</b> você vê o nome, o celular e o e-mail guardados, corrige o que
        quiser e, em <b>Apagar meus dados</b>, apaga tudo isso. As suas opiniões nas Indicações
        ficam à vista na página de cada prestador, nas <b>Indicações</b>. A conta do apartamento
        continua existindo e volta para a senha inicial. Saem junto as suas opiniões e os seus
        avisos nas Indicações; o prestador que você indicou continua na lista, sem ligação com o
        apartamento. Para apagar só uma opinião, use “Apagar a minha opinião” na página do
        prestador.
      </p>
      <p>
        <b>Apagar meus dados</b> também apaga de vez os seus anúncios dos Classificados, com as
        fotos, e os avisos que você mandou sobre anúncios.
      </p>
      <p>
        Um prestador que não quer aparecer nas Indicações pode pedir à Comissão para sair da lista. O
        telefone dele fica guardado só para ele não ser indicado de novo.
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
