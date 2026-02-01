import os
import time
import asyncio
from typing import Dict
from app.core.config import settings
from app.core.logging import logger

class ConversationLogger:
    def __init__(self, storage_path: str = "recordings"):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        
        # Open file handles: {session_id: file_handle}
        self.files: Dict[str, any] = {}
        self.locks: Dict[str, asyncio.Lock] = {}

    def _get_filename(self, session_id: str, participant_id: str) -> str:
        # Standardize naming: session_timestamp_participant.raw
        # Use simple PCM format (s16le)
        return os.path.join(self.storage_path, f"{session_id}_{participant_id}.pcm")

    async def log_audio(self, session_id: str, participant_id: str, audio_data: bytes):
        key = f"{session_id}_{participant_id}"
        
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
            
        async with self.locks[key]:
            if key not in self.files:
                filename = self._get_filename(session_id, participant_id)
                try:
                    self.files[key] = open(filename, "wb")
                    logger.info(f"Started recording for {key} at {filename}")
                except Exception as e:
                    logger.error(f"Failed to open recording file for {key}: {e}")
                    return

            try:
                # Write raw bytes. 
                # Note: If opus, we are writing raw opus packets which is hard to decode without framing.
                # If PCM, easy.
                # Assuming the pipeline sends *decoded* PCM to this logger? 
                # OR we log the raw input. 
                # If we use Google STT, likely we have PCM. 
                # Let's assume we are logging the raw input bytes which are currently Opus-encoded (?)
                # Wait, client sends MessagePack -> AudioPayload. AudioPayload has 'audio_data'.
                # In current test client, it's fake bytes.
                # In real scenario, browser sends PCM or Opus. 
                # If Opus, we should probably save as .opus or frame it.
                # For simplicity, we just append bytes. The decoder script will need to know format.
                self.files[key].write(audio_data)
                self.files[key].flush()
            except Exception as e:
                logger.error(f"Failed to write audio log for {key}: {e}")

    async def close_session(self, session_id: str, participant_id: str):
        key = f"{session_id}_{participant_id}"
        if key in self.files:
            try:
                self.files[key].close()
                del self.files[key]
                if key in self.locks:
                    del self.locks[key]
                logger.info(f"Closed recording for {key}")
            except Exception as e:
                logger.error(f"Error closing recording {key}: {e}")

conversation_logger = ConversationLogger()
