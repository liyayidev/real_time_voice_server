from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Optional, Union
import msgpack
import json

class MessageType(str, Enum):
    # Control
    AUTH = "auth"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    ROOM_INFO = "room_info"
    ERROR = "error"
    SYSTEM = "system"
    
    # Audio
    AUDIO_STREAM = "audio_stream"
    
    # AI
    AI_REQUEST = "ai_request"
    AI_RESPONSE = "ai_response"

class BaseMessage(BaseModel):
    type: MessageType
    payload: Any = Field(default_factory=dict)
    
    def to_msgpack(self) -> bytes:
        return msgpack.packb(self.model_dump(), use_bin_type=True)
    
    @classmethod
    def from_msgpack(cls, data: bytes) -> 'BaseMessage':
        unpacked = msgpack.unpackb(data, raw=False)
        return cls(**unpacked)
    
    def to_json(self) -> str:
        return self.model_dump_json()

# Specific Payload Models (Optional but good for documentation)
class AuthPayload(BaseModel):
    token: str

class JoinRoomPayload(BaseModel):
    room_id: str
    username: str

class AudioPayload(BaseModel):
    # This might not be used directly if we send raw bytes for efficiency,
    # but good for structure if wrapping in msgpack
    participant_id: str
    audio_data: bytes # Raw Opus frames
    timestamp: int
