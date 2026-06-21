from pathlib import Path
from typing import Optional, Dict
import hashlib
from django.conf import settings

try:
    # prefer project-level hash_service if available
    import hash_service
    _file_sha256 = hash_service.file_sha256
except Exception:
    def _file_sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

from frontend.models import MedicalReport, BlockchainRecord
from blockchain.blockchain_service import verify_report_hash, is_chain_valid


def compute_report_hash(report: MedicalReport, use_encrypted: bool = True) -> Optional[str]:
    """Compute SHA-256 for a report file. Prefer encrypted file if present."""
    path = None
    if use_encrypted and getattr(report, 'encrypted_file', None) and getattr(report.encrypted_file, 'path', None):
        path = Path(report.encrypted_file.path)
    elif getattr(report, 'original_file', None) and getattr(report.original_file, 'path', None):
        path = Path(report.original_file.path)

    if not path or not path.exists():
        return None

    safe_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(safe_root):
            return None
    except Exception:
        return None

    return _file_sha256(path)


def verify_report_integrity(report: MedicalReport) -> Dict[str, Optional[bool]]:
    """Verify report integrity locally and against any blockchain records.

    Returns a dict with local_hash, stored_hash, local_match, blockchain_match
    """
    local_hash = compute_report_hash(report)
    stored_hash = report.hash_value or getattr(report, 'file_hash', None)
    local_match = None
    blockchain_match = None

    if local_hash and stored_hash:
        local_match = (local_hash == stored_hash)

    # check latest blockchain record for this report
    bc = report.blockchain_records.order_by('-created_at').first()
    if bc and local_hash:
        blockchain_match = verify_report_hash(local_hash, bc.transaction_reference)

    chain_valid = is_chain_valid()

    return {
        'local_hash': local_hash,
        'stored_hash': stored_hash,
        'local_match': local_match,
        'blockchain_match': blockchain_match,
        'chain_valid': chain_valid,
        'blockchain_record': bc,
    }
