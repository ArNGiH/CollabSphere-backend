from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.models.user import User
from app.schemas.auth import RegisterRequest
from sqlalchemy import or_
from datetime import datetime,timedelta
from jose import jwt
from app.core.config import settings
import uuid
from typing import Optional

pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")

def hash_password(password:str) -> str:
    return pwd_context.hash(password)


def create_user(data:RegisterRequest,db:Session)->User:
    existing_user=db.query(User).filter((User.email==data.email)| (User.username==data.username)).first()

    if(existing_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email or username already exists'
        )
    
    new_user= User(
        id=uuid.uuid4(),
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        is_active=True,
        is_verified=False,
        public_key=data.public_key
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def verify_password(plain_password:str,hashed_password:str)->bool:
    return pwd_context.verify(plain_password,hashed_password)


def authenticate_user(email:str,password:str,db:Session)->User:
    user=db.query(User).filter(User.email==email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No user with this email exists'
        )
    
    if not verify_password(password,user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid email or password'
        )
    return user

def create_access_token(data:dict,expires_delta:timedelta=timedelta(minutes=60))->str:
    to_encode=data.copy()
    expire=datetime.utcnow()+expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt=jwt.encode(to_encode,settings.SECRET_KEY,algorithm="HS256")
    return encoded_jwt


def search_other_users(db: Session, current_user_id, q: Optional[str], limit: int):
    stmt = db.query(User).filter(User.id != current_user_id)

    if q:
        like = f"%{q}%"
        stmt = stmt.filter(
            or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.email.ilike(like),
            )
        )

    stmt = stmt.order_by(User.full_name.asc(), User.username.asc())

    return stmt.limit(limit).all()