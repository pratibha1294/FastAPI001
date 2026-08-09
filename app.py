from fastapi import FastAPI
from pydantic import BaseModel
from repo import register


app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}

@app.get("/health")
def health():
    return {"status": "ok"}

class RegisterRequestDto(BaseModel):
    email: str
    password: str

@app.post("/register")
def register_user(request: RegisterRequestDto):
    register(request.email, request.password)
    # Here you would typically add logic to save the user to a database
    return {"message": "User registered successfully", "user": request}
