from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

# Configuración de MongoDB
MONGO_URI = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URI)
db = client["engine_events_db"]
collection = db["events"]

# Configuración de CORS
origins = [
    "*"  # Permitir cualquier origen (puedes restringirlo)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Esquema de datos
class EventData(BaseModel):
    powerunit_vin: str
    powerunit_id: str
    hardware_type: str
    ignition: bool
    wheels_in_motion: bool
    location: dict
    engine_parameters: dict

class Event(BaseModel):
    event: str
    count: int
    timestamp: int
    data: list[EventData]

# WebSocket manager para manejar conexiones
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# Endpoint WebSocket para datos en tiempo real
@app.websocket("/ws/events/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Guarda los datos en MongoDB
            await collection.insert_one(data)
            # Notifica a los clientes conectados
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Endpoint para obtener eventos almacenados
@app.get("/events/")
async def get_events():
    events = []
    async for event in collection.find():
        event["_id"] = str(event["_id"])
        events.append(event)
    return events
