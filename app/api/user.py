from fastapi import APIRouter,Depends ,HTTPException
from sqlalchemy.orm import Session
from app.schemas.auth import UserResponse
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.schemas.user import UserSummary ,UserDetail
from app.models.user import User
from typing import List
from uuid import UUID
from app.services.auth_service import get_all_other_users

router = APIRouter(
    tags=["Users"]
)

@router.get("/me",response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user


@router.get("/users",response_model=List[UserSummary])
def list_users(db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    users=get_all_other_users(db,current_user.id)
    return users


@router.get("/users/{user_id}",response_model=UserDetail)
def get_user_by_id(user_id:UUID,db:Session=Depends(get_db),current_user: User = Depends(get_current_user)):
    user=db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    return user

@router.get("/users/{user_id}/status")
def get_user_status(user_id:UUID,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail='User not found'
        )
    return{
        "is_online":user.is_online,
        "last_seen":user.last_seen.isoformat() if user.last_seen else None
    }

