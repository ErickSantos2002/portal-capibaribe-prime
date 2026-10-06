"""Esqueci a senha (H-04). **Pertence ao épico B** do M2.

Contrato: `docs/superpowers/specs/m2-contrato.md`, seção 4.3. Nesta onda só existe o lugar
marcado de `processar_pedido`, que a rota já agenda.

**`processar_pedido(login)` roda depois da resposta** (`segundo_plano.agendar`, revisão do
contrato, achado 3): a rota não abre o banco, então o tempo de resposta é o mesmo para qualquer
apartamento. O épico B escreve aqui, abrindo a própria sessão (`fabrica_de_sessoes()`):

1. unidade ativa, ativada e com e-mail pelo login; se não houver, `motivo = "sem_email"`;
2. `config_email()` ligada, senão `motivo = "desligado"`;
3. `reservar_email_recuperacao(db)` (trava da cota), senão `motivo = "cota"`;
4. INSERT do token (`secrets.token_urlsafe(32)`, guardado como `sha256`); as restrições
   `token_recuperacao_limite_hora`/`_dia` viram `motivo = "limite"`;
5. histórico `recuperacao_pedida` (ação do sistema, entidade `unidade`, `{"enviado",
   "motivo"}`) **só para unidade que existe e no máximo uma vez por unidade por hora**
   (`registrado_recentemente`), para um script contra os 320 logins não encher o banco;
6. commit (solta a trava) e, só então, o e-mail com o link (token em texto só na memória).

Nada aqui levanta para fora: erro vira log sem dado pessoal (nem login com e-mail, nem token).

Também do épico B: conferir e usar o link (`conferir`, `redefinir`).
"""


def processar_pedido(login: str) -> None:
    """Pedido de link de recuperação, depois da resposta. Épico B implementa."""
