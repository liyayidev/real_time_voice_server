from typing import AsyncGenerator
from app.services.ai.base import AIAgentBase
from app.services.audio import AudioFrame
from app.core.logging import logger

class EchoAgent(AIAgentBase):
    """
    Simple agent that echoes back the audio it receives, possibly with a delay.
    Useful for testing latency and pipeline.
    """
    async def process_audio_stream(self, audio_stream: AsyncGenerator[AudioFrame, None]) -> AsyncGenerator[AudioFrame, None]:
        logger.info("EchoAgent started processing stream")
        async for frame in audio_stream:
            # Pass through audio
            yield frame
    
    async def process_text_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        async for text in text_stream:
            yield f"Echo: {text}"
