from jwt import create
import repo

def login(email: str,password: str):
    user = repo.login(email,password)
    if user is not None:
        return create(user["id"], claims={"email": email})
    else:
        return None
