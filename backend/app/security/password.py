"""Password hashing and verification helpers."""

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


__all__ = ["hash_password", "verify_password"]
