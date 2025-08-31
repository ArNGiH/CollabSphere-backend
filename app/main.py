from fastapi import FastAPI
from app.api import auth,user,chat,media,ai
from app.websockets.ws_chat import router as ws_router
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,         
    allow_credentials=True,
    allow_methods=["*"],            
    allow_headers=["*"],            
)

app.include_router(auth.router,prefix='/auth',tags=["Auth"])
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(ws_router)
app.include_router(media.router)
app.include_router(ai.router)
@app.get('/')
def root():
    
    return {"message":"Welcome to the application"}


for route in app.routes:
    print(f"{route.path} → {route.name} ({getattr(route, 'methods', ['WS'])})")

