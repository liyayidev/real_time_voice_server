import asyncio
from typing import Dict, Optional, Set
import uuid
from app.models.room import Room, Participant, WebSocketParticipant, VirtualParticipant
from app.core.logging import logger
from app.core.protocol import MessageType, BaseMessage
from app.services.ai_service import agent_manager
from app.services.audio import AudioFrame

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {} # Map participant_id -> Task

    def get_or_create_room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            logger.info(f"Creating new room: {room_id}")
            self.rooms[room_id] = Room(room_id)
        return self.rooms[room_id]

    def remove_room(self, room_id: str):
        if room_id in self.rooms:
            logger.info(f"Removing room: {room_id}")
            # Ensure we clean up any agents in this room?
            # Ideally agents leave when room closes or they are kicked
            del self.rooms[room_id]

    async def join_room(self, room_id: str, participant: Participant):
        room = self.get_or_create_room(room_id)
        room.add_participant(participant)
        
        logger.info(f"Participant {participant.username} joined room {room_id}")
        
        # Notify others
        await self.broadcast_message(
            room_id, 
            BaseMessage(
                type=MessageType.SYSTEM, 
                payload={"message": f"{participant.username} has joined the room"}
            ),
            exclude_id=participant.id
        )

    async def leave_room(self, room_id: str, participant_id: str):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            room.remove_participant(participant_id)
            
            logger.info(f"Participant {participant_id} left room {room_id}")
            
            # Clean up agent task if it was a virtual participant
            if participant_id in self.agent_tasks:
                self.agent_tasks[participant_id].cancel()
                del self.agent_tasks[participant_id]
            
            # Notify others
            await self.broadcast_message(
                room_id,
                BaseMessage(
                    type=MessageType.SYSTEM,
                    payload={"message": f"Participant {participant_id} has left"}
                )
            )
            
            if room.is_empty():
                self.remove_room(room_id)

    async def broadcast_bytes(self, room_id: str, data: bytes, exclude_id: Optional[str] = None):
        """Used for audio broadcasting"""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            tasks = []
            
            # Log the audio (fire and forget task?)
            # We need to parse who it came FROM to log effectively.
            # But broadcast_bytes interface doesn't strictly say who sent it, only exclude_id.
            # Usually exclude_id IS the sender.
            if exclude_id:
                # We need to extract the raw audio payload from the MessagePack if we want PURE audio,
                # otherwise we are logging the MsgPack structure.
                # For now, let's log the raw bytes as they are broadcasted (MsgPack).
                # The decoder will have to handle MsgPack stripping if needed.
                from app.services.recording import conversation_logger
                # Async log - create task to avoid blocking broadcast?
                # For safety in async loop, direct await is safer if method is async.
                tasks.append(conversation_logger.log_audio(room_id, exclude_id, data))

            for p in room.get_participants():
                if exclude_id and p.id == exclude_id:
                    continue
                tasks.append(p.send_bytes(data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_message(self, room_id: str, message: BaseMessage, exclude_id: Optional[str] = None):
        """Used for control messages"""
        if room_id in self.rooms:
            data = message.model_dump()
            room = self.rooms[room_id]
            tasks = []
            for p in room.get_participants():
                if exclude_id and p.id == exclude_id:
                    continue
                tasks.append(p.send_json(data))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def add_agent_to_room(self, room_id: str, agent_name: str = "echo"):
        """
        Spawns a VirtualParticipant backed by an AIAgent and connects loops.
        """
        agent_id = f"agent-{uuid.uuid4().hex[:6]}"
        agent_username = f"AI-{agent_name}"
        
        input_queue = asyncio.Queue()
        agent_participant = VirtualParticipant(agent_id, agent_username, input_queue)
        
        await self.join_room(room_id, agent_participant)
        
        # Start the Agent Processing Loop
        # This reads from input_queue -> agent -> broadcasts back to room
        task = asyncio.create_task(
            self._run_agent_loop(room_id, agent_participant, agent_name)
        )
        self.agent_tasks[agent_id] = task
        
        return agent_id

    async def _run_agent_loop(self, room_id: str, participant: VirtualParticipant, agent_name: str):
        logger.info(f"Starting agent loop for {participant.username}")
        agent_service = agent_manager.get_agent(agent_name)
        
        # Generator that yields audio frames from the queue
        async def audio_source():
            while True:
                data = await participant.input_queue.get()
                # Assuming data is raw opus bytes for now? 
                # Or wrapped in MsgPack? 
                # If broadcast_bytes sends RAW BYTES, then we get raw bytes.
                # If we wrapped it, we need to unwrap.
                # Current simple_client sends MsgPack'd "AUDIO_STREAM".
                # But ws_endpoints.py broadcasts `data` which is the RAW MESSAGE from websocket.
                # Wait, ws_endpoints.py does: unpacked = msgpack.unpackb(data) ... then broadcast_bytes(data)
                # So we are receiving the FULL MSG PACKED BLOB.
                
                # We need to extract the audio payload.
                try:
                    import msgpack
                    unpacked = msgpack.unpackb(data, raw=False)
                    if isinstance(unpacked, dict) and unpacked.get("type") == "audio_stream":
                        payload = unpacked.get("payload", {})
                        audio_bytes = payload.get("audio_data") # This might be bytes
                        if audio_bytes:
                             # Yield an AudioFrame
                             yield AudioFrame(audio_bytes, timestamp=payload.get("timestamp", 0))
                except Exception as e:
                    logger.error(f"Agent decode error: {e}")
                    continue

        try:
            # Connect source to agent
            output_stream = agent_service.process_audio_stream(audio_source())
            
            async for output_frame in output_stream:
                # Wrap output frame back into our protocol
                # Since we want to broadcast it to the room
                import msgpack
                
                msg = {
                    "type": "audio_stream",
                    "payload": {
                        "participant_id": participant.id,
                        "audio_data": output_frame.data,
                        "timestamp": output_frame.timestamp or 0
                    }
                }
                packed = msgpack.packb(msg, use_bin_type=True)
                
                # Broadcast as the agent
                await self.broadcast_bytes(room_id, packed, exclude_id=participant.id)
                
        except asyncio.CancelledError:
            logger.info(f"Agent loop cancelled for {participant.username}")
        except Exception as e:
            logger.error(f"Agent loop crashed: {e}")
        finally:
            await self.leave_room(room_id, participant.id)

room_manager = RoomManager()
