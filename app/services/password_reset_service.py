import uuid
import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.password_reset import PasswordResetToken
from app.services.auth_service import hash_password

RESET_TOKEN_EXPIRY_MINUTES=10
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FRONTEND_RESET_URL = os.getenv("FRONTEND_RESET_URL")

def send_reset_email(recepient_email:str,token:str):
    reset_link=f"{FRONTEND_RESET_URL}?token={token}"

    subject="Reset Your Password"
    body = f"""
    Hi there,

    We received a request to reset your password. Click the link below to set a new password:
    
    {reset_link}

    This link will expire in 10 minutes.

    If you didn't request this, just ignore this email.

    Regards,  
    YourApp Team
    """
    msg=MIMEMultipart()
    msg["From"]=SMTP_USER
    msg["To"]=recepient_email
    msg["Subject"]=subject
    msg.attach(MIMEText(body,"plain"))

    with smtplib.SMTP(SMTP_HOST,SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER,SMTP_PASS)
        server.send_message(msg)
    print(f"Sent password reset link to {recepient_email}")



def create_password_reset_token(email:str,db:Session)->str:
    user=db.query(User).filter(User.email==email).first()
    
    if not user:
        raise HTTPException(status_code=200,detail="If the email is valid , you will get a reset link")
    
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id==user.id).delete()

    token=str(uuid.uuid4())
    expires_at=datetime.now(timezone.utc)+timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)

    db.add(PasswordResetToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at
    ))
    db.commit()
    send_reset_email(user.email,token)
    
    return token


def reset_password(token:str,new_password:str,db:Session):
    record=db.query(PasswordResetToken).filter(PasswordResetToken.token==token).first()

    if not record:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token"
        )
    
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Token has expired"
        )
    
    user=db.query(User).filter(User.id==record.user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    user.hashed_password=hash_password(new_password)
    db.delete(record)
    db.commit()