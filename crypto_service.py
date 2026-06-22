from cryptography.fernet import Fernet
from config import DATA_DIR, SECRET_KEY_PATH


def get_fernet():
    DATA_DIR.mkdir(exist_ok=True)

    if not SECRET_KEY_PATH.exists():
        key = Fernet.generate_key()
        SECRET_KEY_PATH.write_bytes(key)
    else:
        key = SECRET_KEY_PATH.read_bytes()

    return Fernet(key)


def encrypt_bytes(data: bytes) -> bytes:
    fernet = get_fernet()
    return fernet.encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    fernet = get_fernet()
    return fernet.decrypt(data)