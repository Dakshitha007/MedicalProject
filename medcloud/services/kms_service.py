import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

try:
    from Crypto.Cipher import AES
    from Crypto.Hash import HMAC, SHA256
    from Crypto.Protocol.KDF import HKDF
    from Crypto.Protocol.SecretSharing import Shamir
    from Crypto.Random import get_random_bytes
except ImportError:  # pragma: no cover
    AES = None
    HMAC = None
    SHA256 = None
    HKDF = None
    Shamir = None
    get_random_bytes = None

logger = logging.getLogger(__name__)
KEY_SHARE_DIR = Path(os.getenv('KEY_SHARE_DIR', '/var/medcloud/hsm_shares'))


def _format_share(share_index: int, share_bytes: bytes) -> str:
    return f"{share_index}-{share_bytes.hex()}"


def _prepare_shamir_secret(secret: bytes) -> bytes:
    if HKDF is None or SHA256 is None:
        raise RuntimeError('Crypto.Protocol.KDF.HKDF and SHA256 are required for Shamir secret preparation')
    if len(secret) == 16:
        return secret
    return HKDF(secret, 16, b'', SHA256, context=b'medcloud-shamir-secret')


def _format_double_share(share_index: int, share_a: bytes, share_b: bytes) -> str:
    return f"{share_index}-{share_a.hex()}:{share_b.hex()}"


def _parse_share(raw_share: str) -> Tuple[int, bytes, Optional[bytes]]:
    parts = raw_share.split('-', 1)
    if len(parts) != 2:
        raise ValueError('Malformed key share file.')

    share_index = int(parts[0])
    share_data = parts[1]
    if ':' in share_data:
        left, right = share_data.split(':', 1)
        return share_index, bytes.fromhex(left), bytes.fromhex(right)

    return share_index, bytes.fromhex(share_data), None


def _derive_root_key(secret: bytes) -> bytes:
    if HKDF is None or SHA256 is None:
        raise RuntimeError('Crypto.Protocol.KDF.HKDF and SHA256 are required for root key derivation')
    if len(secret) == 32:
        return secret
    return HKDF(secret, 32, b'', SHA256, context=b'medcloud-root-key')


class KMSClient:
    def __init__(self):
        self.enabled = settings.HSM_ENABLED
        self.provider = settings.HSM_PROVIDER
        self.key_id = settings.HSM_KEY_ID
        self.threshold = settings.HSM_THRESHOLD
        self.party_count = settings.HSM_PARTY_COUNT
        self.share_dir = KEY_SHARE_DIR

    def _get_share_paths(self) -> List[Path]:
        return [self.share_dir / f'{self.key_id}.share.{index + 1}' for index in range(self.party_count)]

    def _load_key_shares(self) -> List[str]:
        shares = []
        for path in self._get_share_paths():
            if path.exists():
                shares.append(path.read_text().strip())
        return shares

    def _reconstruct_root_key(self) -> bytes:
        if self.enabled:
            if self.provider == 'local':
                if Shamir is None:
                    raise RuntimeError('Crypto.Protocol.SecretSharing Shamir is required for local HSM key reconstruction')

                raw_shares = self._load_key_shares()
                if len(raw_shares) < self.threshold:
                    raise RuntimeError(
                        f'Insufficient key shares for root key recovery ({len(raw_shares)}/{self.threshold})'
                    )

                shares = []
                for raw_share in raw_shares[: self.threshold]:
                    share_index, share_bytes, _ = _parse_share(raw_share)
                    shares.append((share_index, share_bytes))

                root_secret = Shamir.combine(shares)
                return self._derive_root_key(root_secret)

            raise RuntimeError(f'Unsupported HSM_PROVIDER: {self.provider}')

        if not settings.DEV_INSECURE_MODE:
            raise RuntimeError('HSM is disabled and DEV_INSECURE_MODE is not enabled; key reconstruction is blocked.')

        env_secret = settings.FILE_ENCRYPTION_SECRET
        if not env_secret:
            raise RuntimeError('FILE_ENCRYPTION_SECRET is required when HSM is disabled for local development fallback')

        return self._derive_root_key(env_secret.encode('utf-8'))

    @staticmethod
    def _derive_root_key(secret: bytes) -> bytes:
        if len(secret) == 32:
            return secret
        if HKDF is None or SHA256 is None:
            raise RuntimeError('Crypto.Protocol.KDF.HKDF and SHA256 are required for root key derivation')
        return HKDF(secret, 32, b'', SHA256, context=b'medcloud-root-key')

    def initialize_key_shares(self, secret: Optional[bytes] = None) -> List[str]:
        if not self.enabled or self.provider != 'local':
            raise RuntimeError('HSM must be enabled with local provider for key share initialization')
        if Shamir is None:
            raise RuntimeError('Crypto.Protocol.SecretSharing Shamir is required for key share initialization')

        self.share_dir.mkdir(parents=True, exist_ok=True)
        root_key = secret or get_random_bytes(32)
        shares = Shamir.split(self.threshold, self.party_count, root_key)
        output_shares = []
        for index, share in enumerate(shares):
            share_index, share_bytes = share
            share_string = _format_share(share_index, share_bytes)
            path = self.share_dir / f'{self.key_id}.share.{index + 1}'
            path.write_text(share_string, encoding='utf-8')
            output_shares.append(share_string)
        return output_shares

    def generate_data_key(self, length: int = 32) -> Tuple[bytes, Dict[str, Any]]:
        if get_random_bytes is None:
            raise RuntimeError('Crypto library is required for data key generation')
        data_key = get_random_bytes(length)
        key_wrap = self.wrap_key(data_key)
        return data_key, key_wrap

    def wrap_key(self, key: bytes) -> Dict[str, Any]:
        if AES is None:
            raise RuntimeError('Crypto library is required for key wrapping')
        root_key = self._reconstruct_root_key()
        iv = get_random_bytes(12)
        cipher = AES.new(root_key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(key)
        return {
            'key_id': self.key_id,
            'iv': iv.hex(),
            'ciphertext': ciphertext.hex(),
            'tag': tag.hex(),
        }

    def unwrap_key(self, wrapped: Dict[str, Any]) -> bytes:
        if AES is None:
            raise RuntimeError('Crypto library is required for key unwrapping')
        root_key = self._reconstruct_root_key()
        iv = bytes.fromhex(wrapped['iv'])
        ciphertext = bytes.fromhex(wrapped['ciphertext'])
        tag = bytes.fromhex(wrapped['tag'])
        cipher = AES.new(root_key, AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def sign(self, message: bytes) -> str:
        if HMAC is None or SHA256 is None:
            raise RuntimeError('Crypto library is required for signing')
        root_key = self._reconstruct_root_key()
        mac = HMAC.new(root_key, digestmod=SHA256)
        mac.update(message)
        return mac.hexdigest()

    def verify(self, message: bytes, signature: str) -> bool:
        if HMAC is None or SHA256 is None:
            raise RuntimeError('Crypto library is required for verification')
        root_key = self._reconstruct_root_key()
        mac = HMAC.new(root_key, digestmod=SHA256)
        mac.update(message)
        try:
            mac.verify(bytes.fromhex(signature))
            return True
        except ValueError:
            return False


def get_kms() -> KMSClient:
    return KMSClient()
