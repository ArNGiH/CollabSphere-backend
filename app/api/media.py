from fastapi import APIRouter,File,UploadFile,Form,HTTPException,Depends
from starlette.responses import JSONResponse
from app.services.upload_to_s3 import upload_file_to_s3
from sqlalchemy.orm import Session
from uuid import UUID
from app.websockets.connection_manager import manager
import json
from typing import Optional
from app.core.security import get_current_user
from app.models.chat import Message
from app.models.user import User
from app.db.sessions import get_db
from app.models.chat import Chat

router=APIRouter(tags=['Media'])

@router.post("/media/upload")

async def upload_media(
    file:UploadFile=File(...),
    chat_id:UUID=Form(...),
    db:Session=Depends(get_db),
    content:Optional[str]=Form(None),
    current_user:User=Depends(get_current_user)
):
    try:
        allowed_types=["image/jpeg","image/jpg","image/png","image/webp","video/mp4","video/quicktime"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400,detail="Unsupported file type")
        
        chat_present=db.query(Chat).filter(Chat.id==chat_id).first()
        
        if not chat_present:
            raise HTTPException(
                status_code=404,
                detail="Chat does not exist"
            )
        file_url=upload_file_to_s3(file,file.content_type,chat_id)

        media_type="image" if file.content_type.startswith("image/") else "video"

        media_message=Message(
            chat_id=chat_id,
            sender_id=current_user.id,
            media_url=file_url,
            encrypted_content=content or "",  
            encrypted_keys={},                 
            media_type=media_type
        )
        db.add(media_message)
        db.commit()
        db.refresh(media_message)

        
        await manager.broadcast(str(chat_id), json.dumps({
            "type": "new_message",
            "data": {
                "message_id": str(media_message.id),
                "chat_id": str(media_message.chat_id),
                "sender_id": str(media_message.sender_id),
                "encrypted_content": media_message.encrypted_content,
                "encrypted_keys": media_message.encrypted_keys,
                "media_url": media_message.media_url,
                "media_type": media_message.media_type,
                "created_at": media_message.created_at.isoformat()
            }
        }))
        return JSONResponse({
            "media_url":file_url,
            "media_type":media_type
        })
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))