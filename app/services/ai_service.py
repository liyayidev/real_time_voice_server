from typing import Dict, AsyncGenerator
import asyncio
from app.core.config import settings
from app.services.ai.base import AIAgentBase
from app.services.ai.echo_agent import EchoAgent
from app.services.ai.conversational_agent import ConversationalAgent
# Providers
from app.services.ai.providers.mock import MockSTTService, MockLLMService, MockTTSService
from app.services.ai.providers.google_stt import GoogleSTTService
from app.services.ai.providers.gemini_llm import GeminiLLMService
from app.services.ai.providers.google_tts import GoogleTTSService
from app.core.logging import logger

class AgentManager:
    def __init__(self):
        # Default mock
        mock_agent = ConversationalAgent(
            stt=MockSTTService(),
            llm=MockLLMService(),
            tts=MockTTSService()
        )
        
        self.agents: Dict[str, AIAgentBase] = {
            "echo": EchoAgent(),
            "mock": mock_agent
        }
        
        # Initialize Google Agent if configured or requested
        # Ideally we lazy load or load if creds exist
        if settings.DEFAULT_AGENT_PROVIDER == "google" or settings.GEMINI_API_KEY:
            try:
                google_agent = ConversationalAgent(
                    stt=GoogleSTTService(),
                    llm=GeminiLLMService(),
                    tts=GoogleTTSService()
                )
                self.agents["google"] = google_agent
                logger.info("Google Agent registered")
            except Exception as e:
                logger.error(f"Failed to register Google Agent: {e}")
    
    def get_agent(self, name: str) -> AIAgentBase:
        # If name is "default", look up settings
        if name == "default":
             name = settings.DEFAULT_AGENT_PROVIDER
        
        return self.agents.get(name, self.agents.get("mock", self.agents["echo"]))

agent_manager = AgentManager()
