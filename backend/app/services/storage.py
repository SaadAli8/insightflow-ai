"""Local filesystem storage shared by the API and workers.

Docker mounts the project-level ./storage_data directory into every Python
container at /app/storage_data. The API writes uploads there, file/website
workers write extracted text there, and the AI worker reads the extracted text.
"""

from pathlib import Path

from app.core.config import settings


def _root() -> Path:
    root = Path(settings.local_storage_path).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    return root.resolve()


def _path_for_key(key: str) -> Path:
    root = _root()
    path = (root / key).resolve()
    if root != path and root not in path.parents:
        raise ValueError("storage key escapes the local storage directory")
    return path


def ensure_storage_root() -> None:
    _root().mkdir(parents=True, exist_ok=True)


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    path = _path_for_key(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def download_bytes(key: str) -> bytes:
    return _path_for_key(key).read_bytes()


def public_path(key: str) -> str:
    return str(_path_for_key(key))
