import asyncio
import time
from typing import List, Optional, Deque
from collections import deque
from app.core.logging import logger
from app.core.config import settings

# Attempt to import opuslib, handle failure gracefully for dev environments
try:
    import opuslib
    OPUS_AVAILABLE = True
except (ImportError, Exception) as e:
    logger.warning(f"Opus library not found or failed to load: {e}. Audio decoding/encoding will be disabled.")
    OPUS_AVAILABLE = False

class AudioFrame:
    def __init__(self, data: bytes, timestamp: int, duration_ms: int = 20):
        self.data = data
        self.timestamp = timestamp
        self.duration_ms = duration_ms

class OpusCodec:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, application='voip'):
        self.sample_rate = sample_rate
        self.channels = channels
        self.encoder = None
        self.decoder = None
        
        if OPUS_AVAILABLE:
            try:
                self.encoder = opuslib.Encoder(sample_rate, channels, application)
                self.decoder = opuslib.Decoder(sample_rate, channels)
            except Exception as e:
                logger.error(f"Failed to initialize Opus codecs: {e}")

    def encode(self, pcm_data: bytes, frame_size: int) -> bytes:
        if not self.encoder:
            return b""
        try:
            return self.encoder.encode(pcm_data, frame_size)
        except Exception as e:
            logger.error(f"Opus encode error: {e}")
            return b""

    def decode(self, opus_data: bytes, frame_size: int = None) -> bytes:
        if not self.decoder:
            return b""
        try:
            # If frame_size is not provided, we might need to parse packet or use a default max
            # For 20ms at 16kHz, frame_size is 320 samples
            # For 20ms at 48kHz, frame_size is 960 samples
            if frame_size is None:
                frame_size = int(self.sample_rate * 0.06) # Max 60ms buffer?
            
            return self.decoder.decode(opus_data, frame_size)
        except Exception as e:
            logger.error(f"Opus decode error: {e}")
            return b""

class JitterBuffer:
    """
    Simple Jitter Buffer for ordering packets and handling basic packet loss/late arrival.
    Stores AudioFrames.
    """
    def __init__(self, buffer_ms: int = 60, frame_duration_ms: int = 20):
        self.buffer_ms = buffer_ms
        self.frame_duration_ms = frame_duration_ms
        self.buffer: List[AudioFrame] = []
        self.last_popped_timestamp = 0
        
    def push(self, frame: AudioFrame):
        # Drop if too old
        if self.last_popped_timestamp > 0 and frame.timestamp < self.last_popped_timestamp:
            return
            
        # Insert sorted
        self.buffer.append(frame)
        self.buffer.sort(key=lambda x: x.timestamp)
        
        # Trim if too large (simple strategy: drop oldest)
        # Ideally we drift handling, but this is basic
        max_frames = (self.buffer_ms * 2) // self.frame_duration_ms # Allow some burst
        if len(self.buffer) > max_frames:
             self.buffer.pop(0)

    def pop(self) -> Optional[AudioFrame]:
        if not self.buffer:
            return None
        
        # Check if we have enough buffered? 
        # For real-time, we might just verify continuity or minimum depth
        # For simplicity: just pop the first available if it's "time"
        
        frame = self.buffer.pop(0)
        self.last_popped_timestamp = frame.timestamp
        return frame
