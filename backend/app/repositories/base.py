from abc import ABC
from datetime import datetime, timezone
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError

from app.core.errors import ConflictError, CorruptDocumentError, NotFoundError

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(ABC, Generic[ModelT]):
    """CRUD genérico de um agregado guardado numa coleção do MongoDB.

    Cada subclasse declara o modelo Pydantic, a coleção, o campo de identidade
    e os índices extras. A conversão documento <-> modelo fica só aqui.
    """

    model: ClassVar[type[BaseModel]]
    collection_name: ClassVar[str]
    id_field: ClassVar[str]
    not_found_message: ClassVar[str] = "Registro não encontrado."
    duplicate_message: ClassVar[str] = "Registro já existe."
    stale_message: ClassVar[str] = "O registro foi alterado por outra ação. Tente de novo."
    extra_indexes: ClassVar[tuple[IndexModel, ...]] = ()
    default_sort: ClassVar[tuple[str, int]] = ("created_at", DESCENDING)

    def __init__(self, database: Any) -> None:
        required = ("model", "collection_name", "id_field")
        if any(getattr(type(self), name, None) is None for name in required):
            raise TypeError(
                f"{type(self).__name__} precisa declarar model, collection_name e id_field."
            )
        self._db = database
        self._collection = database[self.collection_name]

    # -- conversão --------------------------------------------------------

    def _to_document(self, entity: ModelT) -> dict:
        return entity.model_dump()

    def _to_model(self, document: dict) -> ModelT:
        document = dict(document)
        document.pop("_id", None)
        try:
            return self.model.model_validate(document)  # type: ignore[return-value]
        except ValidationError as exc:
            # Documento do banco fora do modelo é falha do servidor, não da requisição.
            # A mensagem não leva o conteúdo do documento (pode ter fala do participante).
            raise CorruptDocumentError(
                f"Documento inválido em {self.collection_name}."
            ) from exc

    def _identity(self, entity: ModelT) -> str:
        return getattr(entity, self.id_field)

    # -- índices ----------------------------------------------------------

    def indexes(self) -> list[IndexModel]:
        identity = IndexModel(
            [(self.id_field, ASCENDING)], unique=True, name=f"{self.id_field}_unico"
        )
        return [identity, *self.extra_indexes]

    async def ensure_indexes(self) -> list[str]:
        return await self._collection.create_indexes(self.indexes())

    # -- CRUD -------------------------------------------------------------

    async def create(self, entity: ModelT) -> ModelT:
        try:
            await self._collection.insert_one(self._to_document(entity))
        except DuplicateKeyError as exc:
            raise ConflictError(self.duplicate_message) from exc
        return entity

    async def get(self, entity_id: str) -> ModelT | None:
        document = await self._collection.find_one({self.id_field: entity_id})
        return None if document is None else self._to_model(document)

    async def get_or_raise(self, entity_id: str) -> ModelT:
        entity = await self.get(entity_id)
        if entity is None:
            raise NotFoundError(self.not_found_message)
        return entity

    async def exists(self, entity_id: str) -> bool:
        return await self._collection.count_documents({self.id_field: entity_id}, limit=1) > 0

    async def save(self, entity: ModelT) -> bool:
        """Atualiza o documento existente. Devolve False se ele não existir.

        Modelos com campo `versao` têm controle otimista de concorrência: só grava
        se o documento ainda estiver na versão lida; senão levanta ConflictError
        (evita que uma cópia velha sobrescreva uma alteração mais nova).
        """
        identity = self._identity(entity)
        query: dict = {self.id_field: identity}
        versioned = hasattr(entity, "versao")
        if versioned:
            expected = entity.versao
            # Documentos anteriores ao versionamento não têm o campo.
            query["versao"] = {"$in": [0, None]} if expected == 0 else expected

        document = self._to_document(entity)
        if hasattr(entity, "updated_at"):
            document["updated_at"] = datetime.now(timezone.utc)
        if versioned:
            document["versao"] = expected + 1
        try:
            result = await self._collection.update_one(query, {"$set": document})
        except DuplicateKeyError as exc:
            raise ConflictError(self.duplicate_message) from exc

        if result.matched_count == 0:
            if versioned and await self.exists(identity):
                raise ConflictError(self.stale_message)
            return False
        if hasattr(entity, "updated_at"):
            entity.updated_at = document["updated_at"]
        if versioned:
            entity.versao = document["versao"]
        return True

    async def delete(self, entity_id: str) -> bool:
        result = await self._collection.delete_one({self.id_field: entity_id})
        return result.deleted_count > 0

    async def list(
        self, filters: dict | None = None, *, limit: int = 100, skip: int = 0
    ) -> list[ModelT]:
        cursor = (
            self._collection.find(filters or {})
            .sort([self.default_sort, (self.id_field, ASCENDING)])
            .skip(skip)
            .limit(limit)
        )
        return [self._to_model(document) for document in await cursor.to_list(length=limit)]

    async def count(self, filters: dict | None = None) -> int:
        return await self._collection.count_documents(filters or {})
