"""
Authentication Endpoints

Simple JWT authentication for dashboard access.
Uses Supabase Auth for user management.
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client


router = APIRouter()


# ============ PYDANTIC MODELS ============

class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response with JWT tokens."""
    access_token: str
    refresh_token: str
    user: dict


# ============ HELPERS ============

def get_supabase() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")  # Use anon key for auth
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY required")
    return create_client(url, key)


# ============ ENDPOINTS ============

@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Login with email and password.

    Returns JWT access token and refresh token.
    Tokens are managed by Supabase Auth.
    """
    supabase = get_supabase()

    try:
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })

        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "role": response.user.user_metadata.get("role", "recruiter")
            }
        }

    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh access token using refresh token.

    Returns new access token and refresh token.
    """
    supabase = get_supabase()

    try:
        response = supabase.auth.refresh_session(refresh_token)

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }

    except Exception as e:
        print(f"❌ Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout():
    """
    Logout (invalidate session).

    Note: Client should also clear tokens from local storage.
    """
    supabase = get_supabase()

    try:
        supabase.auth.sign_out()
        return {"status": "ok", "message": "Logged out successfully"}

    except Exception as e:
        print(f"❌ Logout error: {e}")
        return {"status": "error", "message": str(e)}
