import asyncio
from typing import AsyncGenerator
from google.cloud import texttospeech
from app.services.ai.interfaces import TTSService
from app.services.audio import AudioFrame
from app.core.logging import logger
from app.core.config import settings

class GoogleTTSService(TTSService):
    def __init__(self):
        try:
            self.client = texttospeech.TextToSpeechClient()
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Journey-F" # Expressive voice
            )
            self.audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=settings.SAMPLE_RATE
            )
        except Exception as e:
            logger.error(f"Failed to init Google TTS: {e}")
            self.client = None

    async def synthesize(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[AudioFrame, None]:
        if not self.client:
            return

        # Buffering strategy:
        # TTS works best with full sentences or chunks. 
        # Streaming char-by-char to Google TTS might not be efficient or supported as nicely as OpenAI.
        # We will buffer text until punctuation or reasonable length.
        
        buffer = ""
        
        async for text in text_stream:
            buffer += text
            # Simple heuristic split
            if any(p in text for p in [".", "!", "?", "\n"]):
                # Synthesize buffered
                async for frame in self._synthesize_text(buffer):
                    yield frame
                buffer = ""
        
        # Flush remainder
        if buffer.strip():
             async for frame in self._synthesize_text(buffer):
                    yield frame

    async def _synthesize_text(self, text: str) -> AsyncGenerator[AudioFrame, None]:
        if not text.strip():
            return
            
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Blocking call (wrap in executor?)
            # Google *does* have a new StreamingSynthesize in v1beta1 but standard is unary.
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            # Response audio_content is the full WAV/PCM file including headers if WAV.
            # We asked for LINEAR16, which is raw PCM (usually). 
            # Note: The `audio_encoding` LINEAR16 doc says "Uncompressed 16-bit signed little-endian samples (Linear PCM)."
            # It should be raw bytes.
            
            audio_data = response.audio_content
            # Yield in chunks (AudioFrames)
            chunk_size = 320 # 20ms at 16kHz
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i+chunk_size]
                yield AudioFrame(chunk, timestamp=0) # timestamp calc needed?
                
        except Exception as e:
            logger.error(f"Google TTS Error: {e}")
