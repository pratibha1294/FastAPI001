from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from repo import register,login
import service



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

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
    jwt = service.login(request.email,request.password)
    if jwt!= None: 
        return {"is_success": True, "token": jwt}
    return {"is_success": False}

