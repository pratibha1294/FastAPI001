from fastapi import FastAPI
from pydantic import BaseModel
from repo import register,login



app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}

@app.get("/health")
def health():
    return {"status": "ok"}

class AuthRequestDTO(BaseModel):
    email: str
    password: str

@app.post("/register")
def register_user(request: AuthRequestDTO):
    register(request.email, request.password)
    # Here you would typically add logic to save the user to a database
    return {"message": "User registered successfully", "user": request}

@app.post("/login")
def login_user(request: AuthRequestDTO):
    success = login(request.email,request.password)
    print(success)
    if success!= None: 
        return {"is_success": True}
    return {"is_success": False}

