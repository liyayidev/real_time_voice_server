from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from app.services.audio import AudioFrame

class STTService(ABC):
    @abstractmethod
    async def transcribe(self, audio_stream: AsyncGenerator[AudioFrame, None]) -> AsyncGenerator[str, None]:
        """
        Consumes audio frames and yields transcribed text segments.
        """
        pass

class LLMService(ABC):
    @abstractmethod
    async def chat_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """
        Consumes user text and yields AI response text chunks.
        """
        pass

class TTSService(ABC):
    @abstractmethod
    async def synthesize(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[AudioFrame, None]:
        """
        Consumes text chunks and yields audio frames.
        """
        pass
