from jwt import create
import repo

def login(email: str,password: str):
    user = repo.login(email,password)
    if user is not None:
        return create(user["id"], claims={"email": email})
    else:
        return None

def update_password(userId: int,old_password: str,new_password:str):
    print(userId,type(userId))
    okay = repo.validateUserPassword(userId, old_password)
    if okay:
        repo.updateUserPassword(userId, new_password)
    else:
        raise ValueError("Incorrect Old Password")

