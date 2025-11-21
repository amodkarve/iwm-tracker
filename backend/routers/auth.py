"""
Authentication router
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
try:
    import toml
except ImportError:
    try:
        import tomllib
        toml = None
    except ImportError:
        toml = None

router = APIRouter()
security = HTTPBearer()

# Load passwords from secrets.toml
def load_passwords():
    secrets_path = os.path.join(os.path.dirname(__file__), "..", "..", ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        if toml:
            secrets = toml.load(secrets_path)
            return secrets.get("passwords", {})
        else:
            # Fallback: simple parsing for TOML
            passwords = {}
            with open(secrets_path, 'r') as f:
                content = f.read()
                # Simple parser for [passwords] section
                if '[passwords]' in content:
                    for line in content.split('\n'):
                        line = line.strip()
                        if '=' in line and not line.startswith('[') and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            passwords[key] = value
            return passwords
    return {}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# Simple token storage (in production, use JWT or similar)
TOKENS = {}


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Authenticate user and return token"""
    passwords = load_passwords()
    
    if credentials.username in passwords and passwords[credentials.username] == credentials.password:
        # Generate simple token (in production, use JWT)
        import secrets
        token = secrets.token_urlsafe(32)
        TOKENS[token] = credentials.username
        return LoginResponse(access_token=token, username=credentials.username)
    
    raise HTTPException(status_code=401, detail="Invalid username or password")


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user"""
    token = credentials.credentials
    if token in TOKENS:
        del TOKENS[token]
    return {"message": "Logged out successfully"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    if token not in TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return TOKENS[token]

