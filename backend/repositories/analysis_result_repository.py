from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AnalysisResult
from repositories.base_repository import BaseRepository


class AnalysisResultRepository(BaseRepository[AnalysisResult]):
    model = AnalysisResult

    def __init__(self, db: Session):
        super().__init__(db)

    def find_by_job_id(self, job_id: str) -> AnalysisResult | None:
        return self.db.scalar(select(AnalysisResult).where(AnalysisResult.job_id == job_id))
