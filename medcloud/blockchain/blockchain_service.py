import hashlib
import hmac
import json
import os
import time
import tempfile
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from services.kms_service import get_kms

BLOCKCHAIN_FILE = None
BLOCKCHAIN_ANCHOR_FILE = None
_chain_lock = Lock()


def _get_blockchain_file() -> Path:
    if BLOCKCHAIN_FILE is not None:
        return Path(BLOCKCHAIN_FILE)

    file_path = os.getenv('BLOCKCHAIN_LEDGER_FILE_PATH')
    if file_path:
        return Path(file_path)

    return Path(__file__).resolve().parent / 'chain.json'


def _get_blockchain_anchor_file() -> Path:
    if BLOCKCHAIN_ANCHOR_FILE is not None:
        return Path(BLOCKCHAIN_ANCHOR_FILE)

    anchor_path = os.getenv('BLOCKCHAIN_LEDGER_ANCHOR_PATH')
    if anchor_path:
        return Path(anchor_path)

    return _get_blockchain_file().parent / 'anchor.json'


def _load_private_signing_key(path: str):
    try:
        from django.conf import settings
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        key_path = getattr(settings, 'BLOCKCHAIN_SIGNING_KEY_PATH', path)
        with open(key_path, 'rb') as key_file:
            key_data = key_file.read()
        return serialization.load_pem_private_key(key_data, password=None, backend=default_backend())
    except Exception:
        return None


def _load_public_signing_key(path: str):
    try:
        from django.conf import settings
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        key_path = getattr(settings, 'BLOCKCHAIN_SIGNING_PUBLIC_KEY_PATH', path)
        with open(key_path, 'rb') as key_file:
            key_data = key_file.read()
        return serialization.load_pem_public_key(key_data, backend=default_backend())
    except Exception:
        return None


def _get_blockchain_signing_secret() -> Optional[bytes]:
    try:
        from django.conf import settings
        secret = getattr(settings, 'BLOCKCHAIN_SIGNING_SECRET', None)
    except Exception:
        secret = None

    if not secret:
        secret = os.getenv('BLOCKCHAIN_SIGNING_SECRET')
    return secret.encode('utf-8') if secret else None


def _get_signature_message(block_hash: str, previous_hash: str, data: Dict[str, str]) -> bytes:
    return f"{block_hash}{previous_hash}{json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}".encode('utf-8')


def _sign_message(message: bytes) -> str:
    kms = get_kms()
    if kms.enabled:
        return kms.sign(message)

    private_key = _load_private_signing_key('')
    if private_key is not None:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
        return signature.hex()

    secret = _get_blockchain_signing_secret()
    if secret is None:
        raise RuntimeError('Blockchain signing key or secret is required for ledger signing.')

    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _verify_message(message: bytes, signature: str) -> bool:
    kms = get_kms()
    if kms.enabled:
        return kms.verify(message, signature)

    public_key = _load_public_signing_key('')
    if public_key is None:
        private_key = _load_private_signing_key('')
        if private_key is not None:
            try:
                public_key = private_key.public_key()
            except Exception:
                public_key = None

    if public_key is not None:
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec

            public_key.verify(bytes.fromhex(signature), message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    secret = _get_blockchain_signing_secret()
    if secret is None:
        return False

    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _sign_block(block_hash: str, previous_hash: str, data: Dict[str, str]) -> str:
    message = _get_signature_message(block_hash, previous_hash, data)
    return _sign_message(message)


def _verify_block_signature(block: Dict[str, object]) -> bool:
    signature = block.get('signature', '')
    if not signature:
        return False

    message = _get_signature_message(block.get('hash', ''), block.get('previous_hash', ''), block.get('data', {}))
    kms = get_kms()
    if kms.enabled:
        return kms.verify(message, signature)

    public_key = _load_public_signing_key('')
    if public_key is None:
        private_key = _load_private_signing_key('')
        if private_key is not None:
            try:
                public_key = private_key.public_key()
            except Exception:
                public_key = None

    if public_key is not None:
        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import ec

            public_key.verify(bytes.fromhex(signature), message, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception:
            return False

    secret = _get_blockchain_signing_secret()
    if secret is None:
        return False

    expected = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _serialize_block_contents(index: int, timestamp: float, prev_hash: str, data: Dict[str, str]) -> bytes:
    return f"{index}{timestamp}{prev_hash}{json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)}".encode('utf-8')


def _compute_block_hash(block: Dict[str, object]) -> str:
    index = block.get('index')
    timestamp = block.get('timestamp')
    prev_hash = block.get('previous_hash')
    data = block.get('data', {})
    return hashlib.sha256(_serialize_block_contents(index, timestamp, prev_hash, data)).hexdigest()


def _load_chain() -> dict:
    blockchain_file = _get_blockchain_file()
    with _chain_lock:
        if not blockchain_file.exists():
            return {'chain': []}
        try:
            with blockchain_file.open('r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError as exc:
            raise RuntimeError('Blockchain ledger file is malformed or unreadable.') from exc


def _save_chain(chain_data: dict) -> None:
    blockchain_file = _get_blockchain_file()
    with _chain_lock:
        blockchain_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(dir=str(blockchain_file.parent), prefix='chain_', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                json.dump(chain_data, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp_path, str(blockchain_file))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def _serialize_anchor_contents(chain_length: int, latest_block_hash: Optional[str], latest_block_timestamp: Optional[float], merkle_root: Optional[str], anchor_timestamp: float) -> bytes:
    payload = {
        'anchor_timestamp': anchor_timestamp,
        'chain_length': chain_length,
        'latest_block_hash': latest_block_hash,
        'latest_block_timestamp': latest_block_timestamp,
        'merkle_root': merkle_root,
    }
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _compute_anchor_data(chain_data: dict) -> dict:
    chain = chain_data.get('chain', [])
    if not chain:
        return {
            'chain_length': 0,
            'latest_block_hash': None,
            'latest_block_timestamp': None,
            'merkle_root': None,
        }

    hashes = [block.get('data', {}).get('file_hash') for block in chain if block.get('data', {}).get('file_hash')]
    return {
        'chain_length': len(chain),
        'latest_block_hash': chain[-1].get('hash'),
        'latest_block_timestamp': chain[-1].get('timestamp'),
        'merkle_root': calculate_merkle_root(hashes),
    }


def _load_anchor() -> dict:
    anchor_file = _get_blockchain_anchor_file()
    if not anchor_file.exists():
        raise RuntimeError('Blockchain anchor file is missing.')

    try:
        with anchor_file.open('r', encoding='utf-8') as file:
            anchor_data = json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Blockchain anchor file is malformed.') from exc

    signature = anchor_data.get('signature')
    if not signature:
        raise RuntimeError('Blockchain anchor file signature is missing.')

    expected_payload = _serialize_anchor_contents(
        anchor_data.get('chain_length'),
        anchor_data.get('latest_block_hash'),
        anchor_data.get('latest_block_timestamp'),
        anchor_data.get('merkle_root'),
        anchor_data.get('anchor_timestamp'),
    )
    if not _verify_message(expected_payload, signature):
        raise RuntimeError('Blockchain anchor signature is invalid.')

    return anchor_data


def _save_anchor(chain_data: dict) -> None:
    anchor_data = _compute_anchor_data(chain_data)
    anchor_data['anchor_timestamp'] = time.time()
    anchor_data['signature'] = _sign_message(
        _serialize_anchor_contents(
            anchor_data['chain_length'],
            anchor_data['latest_block_hash'],
            anchor_data['latest_block_timestamp'],
            anchor_data['merkle_root'],
            anchor_data['anchor_timestamp'],
        )
    )

    anchor_file = _get_blockchain_anchor_file()
    anchor_file.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=str(anchor_file.parent), prefix='anchor_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(anchor_data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, str(anchor_file))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _save_chain_and_anchor(chain_data: dict) -> None:
    _save_chain(chain_data)
    try:
        _save_anchor(chain_data)
    except Exception:
        # If anchor persistence fails, rollback the chain to prevent an unanchored block.
        if chain_data.get('chain'):
            chain_data['chain'].pop()
            _save_chain(chain_data)
        raise


def _validate_anchor(chain_data: dict) -> bool:
    anchor_data = _load_anchor()
    expected_anchor = _compute_anchor_data(chain_data)
    if anchor_data.get('chain_length') != expected_anchor['chain_length']:
        return False
    if anchor_data.get('latest_block_hash') != expected_anchor['latest_block_hash']:
        return False
    if anchor_data.get('latest_block_timestamp') != expected_anchor['latest_block_timestamp']:
        return False
    if anchor_data.get('merkle_root') != expected_anchor['merkle_root']:
        return False
    return True


def _remove_last_block(expected_hash: str) -> None:
    chain_data = _load_chain()
    chain = chain_data.get('chain', [])
    if not chain or chain[-1].get('hash') != expected_hash:
        raise RuntimeError('Cannot rollback blockchain: last block does not match expected hash.')

    chain.pop()
    _save_chain(chain_data)
    _save_anchor(chain_data)


def rollback_last_block(expected_hash: str) -> None:
    _remove_last_block(expected_hash)


def _find_report_block(chain: List[dict], report_id: int, file_hash: str, user_id: int) -> Optional[dict]:
    for block in chain:
        data = block.get('data', {})
        if data.get('type') == 'report' and data.get('report_id') == report_id and data.get('file_hash') == file_hash and data.get('user_id') == user_id:
            return block
    return None


def _find_consent_block(chain: List[dict], consent_id: int, signature_hash: str) -> Optional[dict]:
    for block in chain:
        data = block.get('data', {})
        if data.get('type') == 'consent' and data.get('consent_id') == consent_id and data.get('signature_hash') == signature_hash:
            return block
    return None


def _is_valid_timestamp(timestamp: float, previous_timestamp: float = 0.0) -> bool:
    now = time.time()
    if timestamp < previous_timestamp:
        return False
    if timestamp > now + 300:
        return False
    return True


def _create_block(index: int, timestamp: float, prev_hash: str, data: Dict[str, str]) -> Dict[str, object]:
    block_hash = hashlib.sha256(_serialize_block_contents(index, timestamp, prev_hash, data)).hexdigest()
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
    try:
        chain_data = _load_chain()
    except RuntimeError:
        return False

    chain = chain_data.get('chain', [])
    if not chain:
        return True

    try:
        anchor_file = _get_blockchain_anchor_file()
        if anchor_file.exists():
            if not _validate_anchor(chain_data):
                return False
        else:
            # A non-empty chain without an anchor is not acceptable in hardened deployments.
            return False
    except RuntimeError:
        return False

    previous_hash = '0' * 64
    previous_timestamp = 0.0
    for index, block in enumerate(chain):
        if block.get('index') != index + 1:
            return False

        if block.get('previous_hash') != previous_hash:
            return False

        if not _is_valid_timestamp(block.get('timestamp', 0.0), previous_timestamp):
            return False

        recomputed_hash = _compute_block_hash(block)
        if block.get('hash') != recomputed_hash:
            return False

        if not _verify_block_signature(block):
            return False

        previous_hash = block.get('hash')
        previous_timestamp = block.get('timestamp', 0.0)

    return True


def add_report_hash(report_hash: str, report_id: int, user_id: int) -> dict:
    chain_data = _load_chain()
    chain = chain_data.setdefault('chain', [])

    if chain and not is_chain_valid():
        raise RuntimeError('Blockchain ledger integrity failure; cannot append new block.')

    existing_block = _find_report_block(chain, report_id, report_hash, user_id)
    if existing_block is not None:
        return {
            'txid': existing_block['hash'],
            'block_number': existing_block['index'],
            'timestamp': existing_block['timestamp'],
            'previous_hash': existing_block['previous_hash'],
        }

    previous_hash = chain[-1]['hash'] if chain else '0' * 64
    index = len(chain) + 1
    timestamp = time.time()
    block_data = {
        'type': 'report',
        'report_id': report_id,
        'user_id': user_id,
        'file_hash': report_hash,
        'timestamp': timestamp,
    }
    block = _create_block(index, timestamp, previous_hash, block_data)
    chain.append(block)
    _save_chain_and_anchor(chain_data)
    return {
        'txid': block['hash'],
        'block_number': block['index'],
        'timestamp': block['timestamp'],
        'previous_hash': block['previous_hash'],
    }


def add_consent_hash(consent_id: int, patient_id: int, doctor_id: int, scope: str, purpose: str, granted_at: Optional[object], expires_at: Optional[object], revoked: bool, signature_hash: str) -> dict:
    chain_data = _load_chain()
    chain = chain_data.setdefault('chain', [])

    if chain and not is_chain_valid():
        raise RuntimeError('Blockchain ledger integrity failure; cannot append new block.')

    existing_block = _find_consent_block(chain, consent_id, signature_hash)
    if existing_block is not None:
        return {
            'txid': existing_block['hash'],
            'block_number': existing_block['index'],
            'timestamp': existing_block['timestamp'],
            'previous_hash': existing_block['previous_hash'],
        }

    previous_hash = chain[-1]['hash'] if chain else '0' * 64
    index = len(chain) + 1
    timestamp = time.time()
    block_data = {
        'type': 'consent',
        'consent_id': consent_id,
        'patient_id': patient_id,
        'doctor_id': doctor_id,
        'scope': scope,
        'purpose': purpose,
        'granted_at': granted_at.isoformat() if granted_at else None,
        'expires_at': expires_at.isoformat() if expires_at else None,
        'revoked': revoked,
        'signature_hash': signature_hash,
        'timestamp': timestamp,
    }
    block = _create_block(index, timestamp, previous_hash, block_data)
    chain.append(block)
    _save_chain_and_anchor(chain_data)
    return {
        'txid': block['hash'],
        'block_number': block['index'],
        'timestamp': block['timestamp'],
        'previous_hash': block['previous_hash'],
    }


def get_report_history(report_id: int) -> List[dict]:
    try:
        chain_data = _load_chain()
    except RuntimeError:
        return []
    return [block for block in chain_data.get('chain', []) if block.get('data', {}).get('report_id') == report_id]


def get_chain_summary() -> dict:
    try:
        chain_data = _load_chain()
    except RuntimeError:
        return {
            'length': 0,
            'latest_block': None,
            'merkle_root': None,
            'is_valid': False,
        }
    chain = chain_data.get('chain', [])
    hashes = [block.get('data', {}).get('file_hash') for block in chain if block.get('data', {}).get('file_hash')]
    return {
        'length': len(chain),
        'latest_block': chain[-1] if chain else None,
        'merkle_root': calculate_merkle_root(hashes),
        'is_valid': is_chain_valid(),
    }


def verify_report_hash(report_hash: str, txid: str) -> bool:
    if not is_chain_valid():
        return False

    try:
        chain_data = _load_chain()
    except RuntimeError:
        return False

    for block in chain_data.get('chain', []):
        if block.get('hash') == txid:
            if not _verify_block_signature(block):
                return False
            stored_hash = block.get('data', {}).get('file_hash')
            return stored_hash == report_hash
    return False
