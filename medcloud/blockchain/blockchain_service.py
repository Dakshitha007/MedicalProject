import hashlib
import hmac
import json
import os
import time
import tempfile
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

BLOCKCHAIN_FILE = Path(__file__).resolve().parent / 'chain.json'
_chain_lock = Lock()


def _get_blockchain_signing_secret() -> str:
    secret = None
    try:
        from django.conf import settings
        secret = getattr(settings, 'BLOCKCHAIN_SIGNING_SECRET', None)
    except Exception:
        secret = None

    if not secret:
        secret = os.getenv('BLOCKCHAIN_SIGNING_SECRET') or os.getenv('FILE_ENCRYPTION_SECRET')
    if not secret:
        raise RuntimeError('BLOCKCHAIN_SIGNING_SECRET or FILE_ENCRYPTION_SECRET environment variable is required for blockchain signing.')
    return secret


def _sign_block(block_hash: str, previous_hash: str, data: Dict[str, str]) -> str:
    message = f"{block_hash}{previous_hash}{json.dumps(data, sort_keys=True)}".encode('utf-8')
    key = _get_blockchain_signing_secret().encode('utf-8')
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _verify_block_signature(block: Dict[str, object]) -> bool:
    block_hash = block.get('hash', '')
    previous_hash = block.get('previous_hash', '')
    data = block.get('data', {})
    signature = block.get('signature', '')
    expected = _sign_block(block_hash, previous_hash, data)
    return hmac.compare_digest(expected, signature)


def _compute_block_hash(block: Dict[str, object]) -> str:
    payload = {
        'index': block.get('index'),
        'timestamp': block.get('timestamp'),
        'previous_hash': block.get('previous_hash'),
        'data': block.get('data', {}),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()


def _load_chain() -> dict:
    with _chain_lock:
        if not BLOCKCHAIN_FILE.exists():
            return {'chain': []}
        try:
            with BLOCKCHAIN_FILE.open('r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise RuntimeError('Blockchain ledger file is malformed or unreadable.') from exc


def _save_chain(chain_data: dict) -> None:
    with _chain_lock:
        BLOCKCHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=str(BLOCKCHAIN_FILE.parent), prefix='chain_', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(chain_data, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, str(BLOCKCHAIN_FILE))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def _create_block(index: int, timestamp: float, prev_hash: str, data: Dict[str, str]) -> Dict[str, object]:
    block_string = f"{index}{timestamp}{prev_hash}{json.dumps(data, sort_keys=True)}"
    block_hash = hashlib.sha256(block_string.encode('utf-8')).hexdigest()
    signature = _sign_block(block_hash, prev_hash, data)
    return {
        'index': index,
        'timestamp': timestamp,
        'previous_hash': prev_hash,
        'hash': block_hash,
        'signature': signature,
        'data': data,
    }


def _hash_pair(left: str, right: str) -> str:
    return hashlib.sha256(f"{left}{right}".encode('utf-8')).hexdigest()


def calculate_merkle_root(hashes: List[str]) -> Optional[str]:
    if not hashes:
        return None

    current_level = hashes[:]
    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            next_level.append(_hash_pair(current_level[i], current_level[i + 1]))
        current_level = next_level

    return current_level[0]


def get_chain() -> dict:
    return _load_chain()


def get_latest_block() -> Optional[dict]:
    chain_data = _load_chain()
    chain = chain_data.get('chain', [])
    return chain[-1] if chain else None


def is_chain_valid() -> bool:
    chain_data = _load_chain()
    chain = chain_data.get('chain', [])

    if not chain:
        return True

    for index, block in enumerate(chain):
        if block.get('index') != index + 1:
            return False

        recomputed_hash = _compute_block_hash(block)
        if block.get('hash') != recomputed_hash:
            return False

        if not _verify_block_signature(block):
            return False

        if index > 0 and block.get('previous_hash') != chain[index - 1].get('hash'):
            return False

    return True


def add_report_hash(report_hash: str, report_id: int, user_id: int) -> dict:
    chain_data = _load_chain()
    chain = chain_data.setdefault('chain', [])
    previous_hash = chain[-1]['hash'] if chain else '0' * 64
    index = len(chain) + 1
    timestamp = time.time()
    block_data = {
        'report_id': report_id,
        'user_id': user_id,
        'file_hash': report_hash,
        'timestamp': timestamp,
    }
    block = _create_block(index, timestamp, previous_hash, block_data)
    chain.append(block)
    _save_chain(chain_data)
    return {
        'txid': block['hash'],
        'block_number': block['index'],
        'timestamp': block['timestamp'],
        'previous_hash': block['previous_hash'],
    }


def get_report_history(report_id: int) -> List[dict]:
    chain_data = _load_chain()
    return [block for block in chain_data.get('chain', []) if block.get('data', {}).get('report_id') == report_id]


def get_chain_summary() -> dict:
    chain_data = _load_chain()
    chain = chain_data.get('chain', [])
    hashes = [block.get('data', {}).get('file_hash') for block in chain if block.get('data', {}).get('file_hash')]
    return {
        'length': len(chain),
        'latest_block': chain[-1] if chain else None,
        'merkle_root': calculate_merkle_root(hashes),
        'is_valid': is_chain_valid(),
    }


def verify_report_hash(report_hash: str, txid: str) -> bool:
    chain_data = _load_chain()
    for block in chain_data.get('chain', []):
        if block.get('hash') == txid:
            if not _verify_block_signature(block):
                return False
            stored_hash = block.get('data', {}).get('file_hash')
            return stored_hash == report_hash
    return False
