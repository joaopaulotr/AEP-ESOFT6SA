class DomainError(Exception):
    """Erro de regra de negócio com mensagem pronta para o usuário (pt-BR)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """O recurso pedido (ou um recurso referenciado por ele) não existe."""


class ConflictError(DomainError):
    """A operação conflita com o estado atual (duplicado, encerrado, inativo, versão velha)."""


class CorruptDocumentError(Exception):
    """Documento gravado no banco não corresponde ao modelo (erro do servidor)."""
