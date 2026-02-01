import asyncio
from typing import AsyncGenerator
from app.services.ai.interfaces import STTService, LLMService, TTSService
from app.services.audio import AudioFrame
from app.core.logging import logger

class MockSTTService(STTService):
    async def transcribe(self, audio_stream: AsyncGenerator[AudioFrame, None]) -> AsyncGenerator[str, None]:
        # Simple energy based detection or just periodic?
        # For mock: assume meaningful audio arrives every X seconds or bytes.
        # We can't easily detect speech in mock without VAD. 
        # So we'll just yield a hardcoded "Hello" after receiving some data.
        
        byte_count = 0
        triggered = False
        
        async for frame in audio_stream:
            byte_count += len(frame.data)
            # Roughly 0.5 seconds of audio (16khz * 2 bytes * 0.5 = 16000 bytes)
            if byte_count > 16000 and not triggered:
                triggered = True
                logger.debug("MockSTT: Detected speech, transcribing...")
                yield "Hello world"
                byte_count = 0
                triggered = False # Reset for next phrase
            
class MockLLMService(LLMService):
    async def chat_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        async for text in text_stream:
            logger.debug(f"MockLLM: Received '{text}'")
            # Simulate thinking
            # await asyncio.sleep(0.5) 
            response = f"I heard you say {text}. That is interesting."
            # Stream token by token
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.1)

class MockTTSService(TTSService):
    async def synthesize(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[AudioFrame, None]:
        async for text in text_stream:
            logger.debug(f"MockTTS: Synthesizing '{text}'")
            # Generate fake audio noise or silence
            # 20ms of silence/noise
            # 16000 Hz * 20ms = 320 samples * 2 bytes = 640 bytes
            dummy_pcm = b'\x00' * 320 # Silence
            # yield a few frames per word
            for _ in range(5):
                yield AudioFrame(dummy_pcm, timestamp=0)
                await asyncio.sleep(0.02)
