import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from auth import get_db, create_access_token, get_current_user, hash_password, verify_password
from database import users_col
from services.email_service import send_welcome_email
from services.profile_service import create_user_profile

router = APIRouter()
logger = logging.getLogger(__name__)

class SignupRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_upper and has_lower and has_digit):
            raise ValueError("Password must contain uppercase, lowercase, and number")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str = None
    is_active: bool
    created_at: datetime

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest):
    existing_user = users_col.find_one({
        "$or": [{"email": request.email}, {"username": request.username}]
    })
    
    if existing_user:
        if existing_user["email"] == request.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail="Username already taken")
    
    user_id = str(ObjectId())
    
    user = {
        "id": user_id,
        "email": request.email,
        "username": request.username,
        "password_hash": hash_password(request.password),
        "full_name": request.full_name,
        "is_active": True,
        "is_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    try:
        users_col.insert_one(user)
        create_user_profile(user_id)
        send_welcome_email(user["email"], user["username"])
        
        access_token = create_access_token(data={"sub": str(user_id)})
        logger.info(f"[AUTH] New user registered: {user['email']}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "is_active": user["is_active"]
            }
        }
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Email or username already exists")
    except Exception as e:
        logger.error(f"[AUTH] Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = users_col.find_one({"email": request.email})
    
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    users_col.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    access_token = create_access_token(data={"sub": str(user["id"])})
    logger.info(f"[AUTH] User logged in: {user['email']}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "is_active": user["is_active"]
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "is_active": current_user.get("is_active", True),
        "created_at": current_user["created_at"]
    }

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    logger.info(f"[AUTH] User logged out: {current_user['email']}")
    return {"message": "Successfully logged out"}
