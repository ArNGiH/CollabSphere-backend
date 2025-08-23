from fastapi import APIRouter,Depends ,HTTPException , Query
from sqlalchemy.orm import Session
from app.schemas.auth import UserResponse
from app.db.sessions import get_db
from app.core.security import get_current_user
from app.schemas.user import UserSummary ,UserDetail
from app.models.user import User
from typing import List,Optional
from uuid import UUID
from app.services.auth_service import search_other_users

router = APIRouter(
    tags=["Users"]
)

@router.get("/me",response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return current_user


@router.get("/users", response_model=List[UserSummary])
def list_users(
    q: Optional[str] = Query(None, alias="query", min_length=1, description="Search by username/full_name/email"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return search_other_users(db, current_user.id, q, limit)


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

