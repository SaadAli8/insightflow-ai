from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: str) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT, *, commit: bool = False, refresh: bool = False) -> ModelT:
        self.db.add(entity)
        if commit:
            self.db.commit()
            if refresh:
                self.db.refresh(entity)
        return entity
