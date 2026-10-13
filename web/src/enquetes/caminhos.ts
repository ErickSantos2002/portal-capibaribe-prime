// M4 · Os endereços das telas de enquete (spec do M4, seção 4). Comum: um épico aponta para a
// tela do outro por aqui, sem importar nada dele.

/** Lista "Abertas / Terminadas" (épico B). */
export const CAMINHO_ENQUETES = '/enquetes'

/** Formulário "Nova enquete" (épico A, só a gestão). */
export const CAMINHO_NOVA_ENQUETE = '/enquetes/nova'

/** Enquete aberta: votar e ver o resultado (épico B). */
export const caminhoEnquete = (id: number) => `/enquetes/${id}`

/** "Quais apartamentos votaram" (épico B, só a gestão). */
export const caminhoVotantes = (id: number) => `/enquetes/${id}/votantes`

/** Editar enquanto ninguém votou (épico A, só a gestão). */
export const caminhoEditarEnquete = (id: number) => `/enquetes/${id}/editar`
