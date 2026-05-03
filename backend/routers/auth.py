from fastapi import APIRouter
from fastapi.responses import RedirectResponse, JSONResponse
import requests, os, jwt
from utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "sigmoidanalytics.com")

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

@router.get("/login")
def login():
    """Redirect user to Google OAuth"""
    auth_url = (
        f"{AUTH_ENDPOINT}?response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&scope=openid%20email%20profile"
        f"%20https://www.googleapis.com/auth/spreadsheets"
        f"%20https://www.googleapis.com/auth/drive.readonly"
        f"&access_type=offline&prompt=consent"
    )
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(code: str):
    """Handle Google callback, issue JWT"""
    # Exchange code for tokens
    resp = requests.post(TOKEN_ENDPOINT, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })

    token_data = resp.json()
    id_token = token_data.get("id_token")
    if not id_token:
        return JSONResponse({"error": "No ID token from Google", "raw": token_data}, status_code=400)

    # Decode without verifying signature
    claims = jwt.decode(id_token, options={"verify_signature": False})

    email = claims.get("email")
    if not email:
        return JSONResponse({"error": "No email in token"}, status_code=400)

    if ALLOWED_DOMAIN and not email.endswith(f"@{ALLOWED_DOMAIN}"):
        return JSONResponse({"error": "Unauthorized domain"}, status_code=403)

    # Issue backend JWT with embedded google token!
    google_token = token_data.get("access_token")
    access_token = create_access_token({"sub": email, "google_token": google_token})

    # 🔑 Return JWT token to React via URL redirect
    redirect_url = f"http://localhost:5173/login?token={access_token}"
    return RedirectResponse(redirect_url)
