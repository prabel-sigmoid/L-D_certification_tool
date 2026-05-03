import os
from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import certificates, sync, auth

app = FastAPI(title="Certificate Management API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(certificates.router)
app.include_router(sync.router)

@app.get("/")
def root():
    return {"message": "Backend running ✅"}
