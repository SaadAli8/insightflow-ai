import uuid


class FileHelper:
    @staticmethod
    def new_storage_key(user_id: str, filename: str) -> str:
        safe_name = filename or "file"
        return f"uploads/{user_id}/{uuid.uuid4()}/{safe_name}"
