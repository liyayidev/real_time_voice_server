from typing import List, Dict, Set
from abc import ABC, abstractmethod
from fastapi import WebSocket
from app.core.logging import logger

class Participant(ABC):
    def __init__(self, id: str, username: str):
        self.id = id
        self.username = username
        self.is_speaking: bool = False
        self.is_muted: bool = False

    @abstractmethod
    async def send_bytes(self, data: bytes):
        pass

    @abstractmethod
    async def send_json(self, data: dict):
        pass

class WebSocketParticipant(Participant):
    def __init__(self, id: str, username: str, websocket: WebSocket):
        super().__init__(id, username)
        self.websocket = websocket
    
    async def send_bytes(self, data: bytes):
        try:
            await self.websocket.send_bytes(data)
        except RuntimeError as e:
            # WebSocket might be closed
            logger.debug(f"Failed to send bytes to {self.username}: {e}")
        except Exception as e:
            logger.error(f"Error sending bytes to {self.username}: {e}")

    async def send_json(self, data: dict):
        try:
            await self.websocket.send_json(data)
        except RuntimeError as e:
            logger.debug(f"Failed to send json to {self.username}: {e}")
        except Exception as e:
            logger.error(f"Error sending json to {self.username}: {e}")

class VirtualParticipant(Participant):
    """
    Represents an AI Agent or Bot in the room.
    Messages sent TO this participant are queued for the Agent to process.
    """
    def __init__(self, id: str, username: str, input_queue):
        super().__init__(id, username)
        self.input_queue = input_queue # asyncio.Queue
        
    async def send_bytes(self, data: bytes):
        # Audio packet received from a human, intended for the agent
        await self.input_queue.put(data)

    async def send_json(self, data: dict):
        # Control message received
        pass

class Room:
    def __init__(self, id: str):
        self.id = id
        self.participants: Dict[str, Participant] = {}
        
    def add_participant(self, participant: Participant):
        self.participants[participant.id] = participant
        
    def remove_participant(self, participant_id: str):
        if participant_id in self.participants:
            del self.participants[participant_id]
            
    def get_participants(self) -> List[Participant]:
        return list(self.participants.values())
        
    def is_empty(self) -> bool:
        return len(self.participants) == 0
