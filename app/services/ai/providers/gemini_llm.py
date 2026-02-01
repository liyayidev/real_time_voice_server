import asyncio
from typing import AsyncGenerator
import google.generativeai as genai
from app.services.ai.interfaces import LLMService
from app.core.logging import logger
from app.core.config import settings

class GeminiLLMService(LLMService):
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-1.5-flash") # or gemini-pro
        else:
            logger.warning("GEMINI_API_KEY not set")
            self.model = None

    async def chat_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        if not self.model:
            yield "Gemini not configured."
            return

        # Start a chat session
        chat = self.model.start_chat(history=[])
        
        async for text in text_stream:
            # Send message and allow streaming response
            try:
                response_stream = await chat.send_message_async(text, stream=True)
                async for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                logger.error(f"Gemini Error: {e}")
