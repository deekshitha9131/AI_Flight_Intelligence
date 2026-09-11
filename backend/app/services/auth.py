from sqlalchemy.orm import Session
from app.repositories.user import get_user_by_email, create_user
from app.schemas.auth import UserCreate, UserLogin
from app.core.security import verify_password, get_password_hash, create_access_token
from fastapi import HTTPException, status

def register_user(db: Session, user: UserCreate):
    # Check if user already exists
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    # Hash password
    hashed_password = get_password_hash(user.password)
    # Create user
    return create_user(db=db, user=user, hashed_password=hashed_password)

def authenticate_user(db: Session, email: str, password: str):
    # Get user by email
    user = get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Verify password
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def login_for_access_token(db: Session, user: UserLogin):
    user = authenticate_user(db, user.email, user.password)
    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}