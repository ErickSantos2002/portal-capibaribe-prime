"""Apoio dos testes do épico B do M3 (anexos nos avisos). Não tem testes.

`enviar(cliente, armazenamento)` faz o que a tela faz com `enviarArquivo`: pede a URL, manda o
conteúdo ao bucket falso e confirma. Devolve o `ArquivoEnviado`.
"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 200
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"0" * 300

__all__ = ["JPEG", "PDF", "anexos_no_banco", "enviar", "pedir_sem_confirmar"]


def _chave(envio: dict) -> str:
    return envio["url"].split("/envios/")[1].split("?")[0]


def pedir_sem_confirmar(
    cliente: TestClient,
    armazenamento,
    *,
    nome: str = "Regras da visita.pdf",
    conteudo: bytes = PDF,
    tipo: str = "application/pdf",
    finalidade: str = "aviso",
) -> dict[str, Any]:
    """Pede e manda ao bucket, sem confirmar: o arquivo fica pendente."""
    resposta = cliente.post(
        "/api/arquivos",
        json={
            "nome": nome,
            "tipo": tipo,
            "finalidade": finalidade,
            "tamanho_bytes": len(conteudo),
        },
    )
    assert resposta.status_code == 201, resposta.text
    envio = resposta.json()
    armazenamento.receber(_chave(envio), conteudo, tipo)
    return envio


def enviar(
    cliente: TestClient,
    armazenamento,
    *,
    nome: str = "Regras da visita.pdf",
    conteudo: bytes = PDF,
    tipo: str = "application/pdf",
    finalidade: str = "aviso",
) -> dict[str, Any]:
    envio = pedir_sem_confirmar(
        cliente, armazenamento, nome=nome, conteudo=conteudo, tipo=tipo, finalidade=finalidade
    )
    resposta = cliente.post(f"/api/arquivos/{envio['arquivo_id']}/confirmar")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def anexos_no_banco(engine: Engine, aviso_id: int) -> list[tuple[int, int, int]]:
    """(versão, ordem, arquivo) de cada anexo do aviso."""
    with engine.connect() as con:
        return [
            (linha.versao, linha.ordem, linha.arquivo_id)
            for linha in con.execute(
                text(
                    "select versao, ordem, arquivo_id from aviso_anexo"
                    " where aviso_id = :a order by versao, ordem"
                ),
                {"a": aviso_id},
            )
        ]
