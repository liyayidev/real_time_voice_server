from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.services.audio import AudioFrame

class AIAgentBase(ABC):
    @abstractmethod
    async def process_audio_stream(self, audio_stream: AsyncGenerator[AudioFrame, None]) -> AsyncGenerator[AudioFrame, None]:
        """
        Consumes an audio stream (user speech) and yields an audio stream (agent response).
        This is the high-level bidirectional loop.
        """
        pass
    
    @abstractmethod
    async def process_text_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """
        Consumes text (transcribed) and yields text (response).
        """
        pass
