from base64 import b64encode, b64decode
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from django.conf import settings

from .kms_service import get_kms

AES_KEY_SIZE = 32
AES_NONCE_SIZE = 12
PBKDF2_SALT_SIZE = 16
PBKDF2_ITERATIONS = 200_000
ENCRYPTION_AAD = b'MedCloudFileEncryptionV1'


def _derive_key(secret: str, salt: bytes) -> bytes:
    return PBKDF2(
        secret.encode('utf-8'),
        salt,
        dkLen=AES_KEY_SIZE,
        count=PBKDF2_ITERATIONS,
        hmac_hash_module=SHA256,
    )


def _build_aad() -> bytes:
    return ENCRYPTION_AAD


def encrypt_file(input_path: Path, output_path: Path, secret_key: str = None) -> dict:
    kms = get_kms()
    if kms.enabled:
        data_key = get_random_bytes(AES_KEY_SIZE)
        wrapped_key = kms.wrap_key(data_key)
    else:
        secret_key = secret_key or settings.FILE_ENCRYPTION_SECRET
        if not secret_key:
            raise ValueError('Encryption secret is required')
        salt = get_random_bytes(PBKDF2_SALT_SIZE)
        data_key = _derive_key(secret_key, salt)

    nonce = get_random_bytes(AES_NONCE_SIZE)
    cipher = AES.new(data_key, AES.MODE_GCM, nonce=nonce)
    cipher.update(_build_aad())

    with input_path.open('rb') as f:
        plaintext = f.read()

    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        f.write(nonce + ciphertext + tag)

    metadata = {
        'version': 1,
        'algorithm': 'AES-256-GCM',
        'nonce': b64encode(nonce).decode('utf-8'),
        'tag': b64encode(tag).decode('utf-8'),
    }
    if kms.enabled:
        metadata['key_wrap'] = wrapped_key
    else:
        metadata.update({
            'key_derivation': 'PBKDF2-HMAC-SHA256',
            'iterations': PBKDF2_ITERATIONS,
            'salt': b64encode(salt).decode('utf-8'),
        })
    return metadata


def decrypt_file(input_path: Path, secret_key: str = None, metadata: dict = None, output_path: Path = None) -> dict:
    if metadata is None:
        raise ValueError('Missing encryption metadata')

    kms = get_kms()
    if kms.enabled and 'key_wrap' in metadata:
        data_key = kms.unwrap_key(metadata['key_wrap'])
    else:
        secret_key = secret_key or settings.FILE_ENCRYPTION_SECRET
        if not secret_key or 'salt' not in metadata:
            raise ValueError('Encryption metadata or secret key is missing')
        salt = b64decode(metadata['salt'])
        data_key = _derive_key(secret_key, salt)

    with input_path.open('rb') as f:
        nonce = f.read(AES_NONCE_SIZE)
        ciphertext_and_tag = f.read()

    ciphertext = ciphertext_and_tag[:-16]
    tag = ciphertext_and_tag[-16:]
    cipher = AES.new(data_key, AES.MODE_GCM, nonce=nonce)
    cipher.update(_build_aad())
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('wb') as f:
            f.write(plaintext)
        return {'decrypted_path': str(output_path)}

    return {'plaintext': plaintext}
