import asyncio
from typing import AsyncGenerator
from app.services.ai.base import AIAgentBase
from app.services.ai.interfaces import STTService, LLMService, TTSService
from app.services.audio import AudioFrame
from app.core.logging import logger

class ConversationalAgent(AIAgentBase):
    def __init__(self, stt: STTService, llm: LLMService, tts: TTSService):
        self.stt = stt
        self.llm = llm
        self.tts = tts
    
    async def process_audio_stream(self, audio_stream: AsyncGenerator[AudioFrame, None]) -> AsyncGenerator[AudioFrame, None]:
        # Verify the pipeline flow:
        # Audio -> STT -> Text
        # Text -> LLM -> Text Stream
        # Text Stream -> TTS -> Audio
        
        # We need to bridge these generators.
        # Since they are all async generators consuming generators, we can chain them directly?
        # STT consumes audio_stream, yields text.
        
        # 1. Transcribe
        text_stream = self.stt.transcribe(audio_stream)
        
        # 2. LLM Chat
        # Note: LLM usually expects a conversation history, but for streaming we might just pipe stt output.
        # A more complex agent would manage context here.
        # But `chat_stream` interface consumes a generator.
        response_text_stream = self.llm.chat_stream(text_stream)
        
        # 3. TTS
        response_audio_stream = self.tts.synthesize(response_text_stream)
        
        async for frame in response_audio_stream:
            yield frame

    async def process_text_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        # Text-only mode fallback
        async for chunk in self.llm.chat_stream(text_stream):
            yield chunk
