"""Apoio dos testes do épico A do M3 (documentos). Não tem testes; o nome segue a posse de
arquivos do épico (contrato do M3, seção 10).

O arquivo de cada documento passa pelo envio de verdade (`POST /api/arquivos`, o bucket falso
fazendo o papel do navegador, `POST /api/arquivos/{id}/confirmar`).
"""

from typing import Any

from fastapi.testclient import TestClient

from testes.conftest import COMISSAO

PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"0" * 200


def enviar_arquivo(
    cliente: TestClient,
    armazenamento,
    *,
    nome: str = "Convenção do condomínio.pdf",
    finalidade: str = "documento",
    conteudo: bytes = PDF,
    confirmar: bool = True,
) -> int:
    """Pede, "manda" e confirma um arquivo como a tela faria; devolve o id."""
    resposta = cliente.post(
        "/api/arquivos",
        json={
            "nome": nome,
            "tipo": "application/pdf",
            "finalidade": finalidade,
            "tamanho_bytes": len(conteudo),
        },
    )
    assert resposta.status_code == 201, resposta.text
    envio = resposta.json()
    chave = envio["url"].split("/envios/")[1].split("?")[0]
    armazenamento.receber(chave, conteudo)
    if confirmar:
        confirmado = cliente.post(f"/api/arquivos/{envio['arquivo_id']}/confirmar")
        assert confirmado.status_code == 200, confirmado.text
    return envio["arquivo_id"]


def corpo(arquivo_id: int, **troca: Any) -> dict[str, Any]:
    return {
        "titulo": "Convenção do condomínio",
        "categoria": "convencao",
        "data_documento": "2026-10-01",
        "acesso": "compradores",
        "arquivo_id": arquivo_id,
        **troca,
    }


def publicar_documento(logar, armazenamento, *, login: str = COMISSAO, **troca: Any) -> dict:
    """Envia o arquivo e publica pela API; devolve o `Documento`."""
    cliente = logar(login)
    arquivo_id = enviar_arquivo(cliente, armazenamento)
    resposta = cliente.post("/api/documentos", json=corpo(arquivo_id, **troca))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def nova_versao(logar, armazenamento, documento_id: int, *, login: str = COMISSAO) -> dict:
    cliente = logar(login)
    arquivo_id = enviar_arquivo(cliente, armazenamento, nome="Versão nova.pdf")
    resposta = cliente.post(
        f"/api/documentos/{documento_id}/versoes", json={"arquivo_id": arquivo_id}
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def arquivar(logar, documento_id: int, *, login: str = COMISSAO) -> dict:
    resposta = logar(login).post(f"/api/documentos/{documento_id}/arquivar")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()
