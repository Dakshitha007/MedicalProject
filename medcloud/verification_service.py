from pathlib import Path
from .hash_service import file_sha256
from .blockchain.blockchain_service import verify_report_hash


def verify_report_integrity(file_path: Path, expected_txid: str) -> bool:
    if not file_path.exists():
        return False
    computed_hash = file_sha256(file_path)
    return verify_report_hash(computed_hash, expected_txid)
