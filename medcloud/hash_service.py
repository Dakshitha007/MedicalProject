import hashlib
from pathlib import Path


def file_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with file_path.open('rb') as file:
        for chunk in iter(lambda: file.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
