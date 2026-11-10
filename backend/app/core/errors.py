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


class FileTooLargeError(DomainError):
    """Arquivo enviado maior que o limite (413)."""


class UnsupportedFileError(DomainError):
    """Extensão de arquivo fora da lista aceita (415)."""


class ImportFileError(DomainError):
    """O conteúdo do arquivo enviado não pôde ser lido (422)."""


class EmptyQuestionnaireError(ImportFileError):
    """Nenhuma pergunta encontrada no arquivo (422)."""
