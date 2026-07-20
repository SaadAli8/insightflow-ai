from fastapi import APIRouter, Depends, File as UploadFileMarker, UploadFile
from sqlalchemy.orm import Session

from config.database import get_db
from middleware import get_current_user
from models import User
from schemas import JobResponse, PresignRequest, PresignResponse
from services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=JobResponse, status_code=202)
def upload_file(
    upload: UploadFile = UploadFileMarker(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FileService(db).upload(upload, user)


@router.post("/presign", response_model=PresignResponse)
def presign_upload(
    body: PresignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FileService.presign_upload_disabled()


@router.post("/{file_id}/complete", response_model=JobResponse, status_code=202)
def complete_upload(
    file_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return FileService(db).complete_upload(file_id, user)
