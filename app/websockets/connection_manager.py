from fastapi import WebSocket
from typing import Dict,List
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections:Dict[str,List[WebSocket]]=defaultdict(list)


    async def connect(self,chat_id:str,websocket:WebSocket):
        await websocket.accept()
        self.active_connections[chat_id].append(websocket)

    def disconnect(self,chat_id:str,websocket:WebSocket):
        if websocket in self.active_connections[chat_id]:
            self.active_connections[chat_id].remove(websocket)

    async def send_personal_message(self,message:str,websocket:WebSocket):
        await websocket.send_text(message)

    async def broadcast(self,chat_id:str,message:str):
        for connection in self.active_connections[chat_id]:
            await connection.send_text(message)



manager = ConnectionManager()