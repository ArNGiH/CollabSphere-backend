from fastapi import FastAPI
from app.api import auth,user,chat

app=FastAPI()

app.include_router(auth.router,prefix='/auth',tags=["Auth"])
app.include_router(user.router)
app.include_router(chat.router)

@app.get('/')
def root():
    return {"message":"Welcome to the application"}

