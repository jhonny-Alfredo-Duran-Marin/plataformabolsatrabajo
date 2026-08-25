import bcrypt


def hash_password(raw_password: str) -> str:
    pwd_bytes = raw_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = raw_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except ValueError:
        return False
