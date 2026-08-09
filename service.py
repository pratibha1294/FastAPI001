from jwt import encrypt
import repo

def login(email: str,password: str):
    user = repo.login(email,password)
    if user is not None:
        return encrypt(user["id"], claims={"email": email})
    else:
        return None
