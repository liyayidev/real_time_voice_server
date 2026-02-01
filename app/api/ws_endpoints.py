from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
import uuid
import msgpack
import asyncio
from app.services.room_manager import room_manager
from app.models.room import WebSocketParticipant
from app.core.protocol import MessageType, BaseMessage
from app.core.logging import logger

router = APIRouter()

@router.websocket("/ws/{room_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, username: str):
    await websocket.accept()
    
    # Simple ID generation
    participant_id = str(uuid.uuid4())
    participant = WebSocketParticipant(participant_id, username, websocket)
    
    await room_manager.join_room(room_id, participant)
    
    # AUTO-ADD AGENT FOR TESTING: If room name starts with 'ai-', add an agent
    if room_id.startswith("ai-") and len(room_manager.rooms.get(room_id).participants) == 1:
        # Auto-select agent based on room name suffix? e.g. ai-mock-...
        agent_name = "mock-conversation" if "mock" in room_id else "echo"
        asyncio.create_task(room_manager.add_agent_to_room(room_id, agent_name))
    
    try:
        while True:
            # We must handle both bytes (audio) and text/json (control)
            # Or assume everything is msgpack?
            # Strategy: Listen for bytes. If it decodes to a known structure, treat as control.
            # Otherwise, assuming efficient packing, maybe use a header byte.
            # For simplicity in this iteration:
            # - Text messages are control (JSON)
            # - Binary messages are Audio (or MsgPack control)
            
            # But the requirement said "Use MessagePack ... for binary data serialization".
            # So potentially everything is binary.
            
            # Let's try to receive message
            message = await websocket.receive()
            
            if "bytes" in message:
                data = message["bytes"]
                # Try to unpack as BaseMessage
                try:
                    unpacked = msgpack.unpackb(data, raw=False)
                    if isinstance(unpacked, dict) and "type" in unpacked:
                        # It is a structured message
                        msg_type = unpacked.get("type")
                        
                        if msg_type == MessageType.AUDIO_STREAM:
                            # Broadcast audio to others in room
                            # We re-pack or just forward?
                            # Optimally we define the packet format to allow forwarding.
                            # For now, let's just broadcast the raw bytes to everyone else.
                            await room_manager.broadcast_bytes(room_id, data, exclude_id=participant_id)
                        
                        elif msg_type == MessageType.LEAVE_ROOM:
                            break
                            
                        else:
                            # Handle other control messages
                            logger.debug(f"Received control message: {msg_type}")
                    else:
                        # Unknown binary format, assume pure audio raw frames?
                        # Dangerous. Let's assume protocol compliance: ALL generic messages are MsgPack'd BaseMessage.
                        pass
                        
                except Exception:
                    # Not valid msgpack, or audio raw fallback?
                    # For safety, ignore or log
                    pass
            
            elif "text" in message:
                # Handle JSON control messages if we support them
                pass
                
    except WebSocketDisconnect:
        logger.info(f"Client {username} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await room_manager.leave_room(room_id, participant_id)
