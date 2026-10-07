// "O que mudou" no Portal, na voz do morador. Regra (README, seção Versões): toda mudança que o
// morador vê ganha item aqui, no mesmo commit, e a primeira entrada é sempre a versão do
// web/package.json. Mais nova primeiro.

export interface Novidade {
  /** Semver: correção sobe o último número; novidade ou marco novo, o do meio. */
  versao: string
  /** Dia em que entrou no ar, AAAA-MM-DD. */
  data: string
  /** Nome curto opcional da versão, como "Lançamento". */
  nome?: string
  itens: string[]
}

/** A versão do Portal: `version` do web/package.json, injetada pelo Vite (vite.config.ts). */
export const VERSAO: string = __VERSAO__

export const NOVIDADES: Novidade[] = [
  {
    versao: '1.2.0',
    data: '2026-10-06',
    nome: 'Avisos no celular',
    itens: [
      'Avisos no celular: ative em Minha unidade e cada aviso novo do seu bloco chega como notificação, com o título. Tocar abre o aviso.',
      'O Portal pode ficar na tela inicial do celular, como um aplicativo. No iPhone, as notificações só chegam com o Portal instalado e aberto pelo ícone.',
      'Quem cadastrou e-mail também recebe os avisos por lá.',
      'Esqueceu a senha? Na tela de entrar, toque em "Esqueci minha senha": se o apartamento tiver e-mail cadastrado, chega um link para criar uma senha nova.',
    ],
  },
  {
    versao: '1.1.1',
    data: '2026-10-06',
    itens: ['No computador, o logo do residencial também aparece no alto do menu lateral.'],
  },
  {
    versao: '1.1.0',
    data: '2026-10-06',
    itens: [
      'O logo do Capibaribe Prime Residence agora recebe você na entrada.',
      'O Portal ganhou ícone próprio: aparece na aba do navegador e quando você salva o Portal na tela inicial do celular.',
      'Esta janela: tocando na versão, você vê o que mudou no Portal.',
    ],
  },
  {
    versao: '1.0.0',
    data: '2026-10-06',
    nome: 'Lançamento',
    itens: [
      'Entrar com o bloco e o apartamento, e criar a sua própria senha no primeiro acesso.',
      'Mural de avisos da Comissão, com categorias (Geral, Obra, Reunião, Financeiro e Urgente), avisos fixados no topo e avisos só para o seu bloco.',
      'Avisos mais fáceis de ler: subtítulos, listas, destaques e um quadro com quando e onde para os eventos.',
      'Selo "Corrigido" quando a Comissão muda um aviso que já tinha saído.',
      'Minha unidade: seus dados, a troca de senha, os aparelhos conectados e a opção de apagar seus dados.',
      'Para a Comissão: publicar avisos, ver quem já leu e a lista de apartamentos.',
      'Política de privacidade explicando o que o Portal guarda e por quê.',
      'Tema claro e escuro, no celular e no computador.',
    ],
  },
]

// A data é só o dia: lida ao meio-dia UTC, nenhum fuso escorrega para o dia anterior.
const porExtenso = new Intl.DateTimeFormat('pt-BR', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

/** "2026-10-06" → "6 de outubro de 2026". */
export function formatarDataDaVersao(data: string): string {
  return porExtenso.format(new Date(`${data}T12:00:00Z`))
}
