from fastapi import FastAPI
from app.api import auth,user,chat,media
from app.websockets.ws_chat import router as ws_router

app=FastAPI()

app.include_router(auth.router,prefix='/auth',tags=["Auth"])
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(ws_router)
app.include_router(media.router)

@app.get('/')
def root():
    return {"message":"Welcome to the application"}

for route in app.routes:
    print(f"{route.path} → {route.name} ({getattr(route, 'methods', ['WS'])})")
