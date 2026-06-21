import logging
from pathlib import Path
from typing import Dict, Optional

from django.conf import settings
from .hash_service import file_sha256
from blockchain.blockchain_service import verify_report_hash
from frontend.models import MedicalReport

logger = logging.getLogger(__name__)


def verify_offchain_integrity(report: MedicalReport) -> Dict[str, Optional[bool]]:
    result = {
        'report_id': report.id,
        'local_hash': None,
        'stored_hash': report.hash_value or report.file_hash,
        'hash_matches': None,
        'blockchain_verified': None,
    }
    if not report.encrypted_file or not report.encrypted_file.path:
        return result

    file_path = Path(report.encrypted_file.path)
    if not file_path.exists():
        return result

    local_hash = file_sha256(file_path)
    result['local_hash'] = local_hash
    stored_hash = result['stored_hash']
    result['hash_matches'] = stored_hash == local_hash if stored_hash else None
    if report.blockchain_txid:
        result['blockchain_verified'] = verify_report_hash(local_hash, report.blockchain_txid)
    return result


def verify_all_reports() -> Dict[str, int]:
    reports = MedicalReport.objects.all()
    summary = {'total': reports.count(), 'mismatch_count': 0, 'blockchain_failures': 0}
    for report in reports:
        result = verify_offchain_integrity(report)
        if result.get('hash_matches') is False:
            summary['mismatch_count'] += 1
        if result.get('blockchain_verified') is False:
            summary['blockchain_failures'] += 1
    logger.info('Integrity summary: %s', summary)
    return summary
