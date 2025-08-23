from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from fastapi import WebSocket

class ConnectionManager:
    # chat_id -> list[(websocket, user_id)]
    def __init__(self):
        self.active: Dict[str, List[Tuple[WebSocket, str]]] = defaultdict(list)

    # NOTE: do NOT call websocket.accept() here. The route will accept first.
    async def connect(self, chat_id: str, user_id: str, websocket: WebSocket):
        self.active[chat_id].append((websocket, user_id))

    def disconnect(self, chat_id: str, websocket: WebSocket):
        conns = self.active.get(chat_id, [])
        if websocket in [ws for (ws, _) in conns]:
            self.active[chat_id] = [(ws, uid) for (ws, uid) in conns if ws is not websocket]
        if not self.active.get(chat_id):
            # optional cleanup
            self.active.pop(chat_id, None)

    async def broadcast(self, chat_id: str, message: str, exclude: Optional[WebSocket] = None):
        conns = list(self.active.get(chat_id, []))  # copy to avoid mutation during loop
        dead: List[WebSocket] = []
        for ws, _uid in conns:
            if exclude is not None and ws is exclude:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        # cleanup dead sockets
        for ws in dead:
            self.disconnect(chat_id, ws)

manager = ConnectionManager()
