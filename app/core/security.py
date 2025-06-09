from datetime import datetime
from jose import JWTError,jwt
from fastapi import HTTPException,status,Depends
from sqlalchemy.orm import Session
from app.core.config import settings,oauth2_scheme
from app.db.sessions import get_db
from app.models.user import User



def decode_access_token(token:str)->dict:
    try:
        payload=jwt.decode(token,settings.SECRET_KEY,algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    

def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db))->User:
    token_str = token.credentials

    payload = decode_access_token(token_str)
    
    user_id:str=payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )
    user=db.query(User).filter(User.id==user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No user found'
        )
    
    return user
