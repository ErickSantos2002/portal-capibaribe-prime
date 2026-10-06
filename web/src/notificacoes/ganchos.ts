// Épico A do M2 · pontos de encaixe nas telas comuns e do M1 (spec do M2, seção 7). Pertence ao
// épico A: ele troca o corpo destas funções, e as telas que as chamam não mudam.
//
// Nesta onda (contrato) nada aparece para o morador: as funções não fazem nada.

/** Chamado uma vez em `main.tsx`, depois de montar o app: registra `/sw.js`. */
export function registrarServiceWorker(): void {}

/** Para onde o primeiro acesso leva (H-05: a oferta única "Instalar" e "Ativar notificações"
 *  vem depois do primeiro acesso). Hoje, o mural, como no M1. */
export function destinoDepoisDoPrimeiroAcesso(): string {
  return '/avisos'
}
