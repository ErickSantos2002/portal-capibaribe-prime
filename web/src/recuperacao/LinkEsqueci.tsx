// Épico B do M2 · o "Esqueci minha senha" da tela de entrada (spec do M2, seção 7). Pertence ao
// épico B, que troca isto por um link para `/esqueci-a-senha`. Nesta onda é o mesmo texto do M1
// (só mudou de arquivo), para o morador não ver diferença.
export function LinkEsqueci() {
  return (
    <details className="acesso-esqueci">
      <summary className="texto-link">Esqueci minha senha</summary>
      <p>
        Fale com a administração do Portal no grupo do WhatsApp. Ela volta a senha do seu
        apartamento para a inicial, e você escolhe uma nova ao entrar.
      </p>
    </details>
  )
}
