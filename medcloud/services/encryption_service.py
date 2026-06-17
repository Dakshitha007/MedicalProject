from base64 import b64encode, b64decode
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

AES_KEY_SIZE = 32
AES_NONCE_SIZE = 12
PBKDF2_SALT_SIZE = 16
PBKDF2_ITERATIONS = 200_000


def _derive_key(secret: str, salt: bytes) -> bytes:
    return PBKDF2(secret.encode('utf-8'), salt, dkLen=AES_KEY_SIZE, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)


def encrypt_file(input_path: Path, output_path: Path, secret_key: str) -> dict:
    salt = get_random_bytes(PBKDF2_SALT_SIZE)
    key = _derive_key(secret_key, salt)
    nonce = get_random_bytes(AES_NONCE_SIZE)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    with input_path.open('rb') as f:
        plaintext = f.read()

    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        f.write(nonce + ciphertext + tag)

    return {
        'algorithm': 'AES-256-GCM',
        'key_derivation': 'PBKDF2-HMAC-SHA256',
        'iterations': PBKDF2_ITERATIONS,
        'salt': b64encode(salt).decode('utf-8'),
        'nonce': b64encode(nonce).decode('utf-8'),
        'tag': b64encode(tag).decode('utf-8'),
    }


def decrypt_file(input_path: Path, secret_key: str, metadata: dict, output_path: Path) -> dict:
    if metadata is None or 'salt' not in metadata:
        raise ValueError('Missing encryption metadata')

    salt = b64decode(metadata['salt'])
    key = _derive_key(secret_key, salt)

    with input_path.open('rb') as f:
        nonce = f.read(AES_NONCE_SIZE)
        ciphertext_and_tag = f.read()

    ciphertext = ciphertext_and_tag[:-16]
    tag = ciphertext_and_tag[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        f.write(plaintext)

    return {
        'decrypted_path': str(output_path),
    }
