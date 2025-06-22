from fastapi import APIRouter,Depends,status
from sqlalchemy.orm import Session
from app.schemas.auth import RegisterResponse,RegisterRequest,LoginRequest,LoginResponse,UserResponse
from app.services.auth_service import create_user,authenticate_user,create_access_token
from app.db.sessions import get_db
from app.services.password_reset_service import create_password_reset_token,reset_password
from app.schemas.password_reset import ForgotPasswordRequest,ResetPasswordRequest


router=APIRouter()

@router.post("/register",response_model=RegisterResponse)
def register_user(data:RegisterRequest,db:Session=Depends(get_db)):
    user=create_user(data,db)
    return RegisterResponse(
        message="Account created . Please verify your email to continue",
        user_id=user.id,
        email_sent=True,
    )

@router.post("/login",response_model=LoginResponse)
def login_user(data:LoginRequest,db:Session=Depends(get_db)):
    user=authenticate_user(data.email,data.password,db)
    
    token_data={
        "sub":str(user.id),
        "email":str(user.email)
    }
    access_token=create_access_token(token_data)
    user_response = UserResponse.model_validate(user)


    return LoginResponse(
        access_token=access_token,
        user=user_response
    )

@router.post("/forgot-password")
def forgot_password(data:ForgotPasswordRequest,db:Session=Depends(get_db)):
    create_password_reset_token(data.email,db)
    return {"message": "If the email is valid, a reset link has been sent."}

@router.post("/reset-password")
def reset_user_password(data:ResetPasswordRequest,db:Session=Depends(get_db)):
    reset_password(data.token,data.new_password,db)
    return {"message": "Password has been reset successfully."}