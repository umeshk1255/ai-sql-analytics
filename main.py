# main.py

from fastapi import FastAPI
from ask import ask_database
from schemas import AskRequest, AskResponse

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI SQL Agent running"}

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    return ask_database(request.query)
