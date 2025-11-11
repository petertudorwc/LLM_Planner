from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from datetime import timedelta
import logging

from ..core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory user database (replace with proper database in production)
# Default credentials: admin/admin
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin"),
        "full_name": "Admin User"
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class UserResponse(BaseModel):
    username: str
    full_name: str

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Authenticate user and return JWT token"""
    user = fake_users_db.get(credentials.username)
    
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {credentials.username} logged in successfully")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"]
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    username = current_user["username"]
    user = fake_users_db.get(username)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user["username"],
        "full_name": user["full_name"]
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    logger.info(f"User {current_user['username']} logged out")
    return {"message": "Logged out successfully"}
