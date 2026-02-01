import redis.asyncio as redis
from .config import settings
from .logging import logger

class RedisClient:
    def __init__(self):
        self.redis: redis.Redis | None = None

    async def connect(self):
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise e

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
            
    async def get(self, key: str):
        return await self.redis.get(key)
        
    async def set(self, key: str, value: str, expire: int = None):
        return await self.redis.set(key, value, ex=expire)
        
    async def delete(self, key: str):
        return await self.redis.delete(key)

redis_client = RedisClient()
