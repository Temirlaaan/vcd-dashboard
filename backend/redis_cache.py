# backend/redis_cache.py
import os
import json
import redis
from typing import Optional, Any
from datetime import timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Конфигурация Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Время жизни кеша (в секундах)
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 минут по умолчанию

class RedisCache:
    """Класс для работы с Redis кешем"""
    
    def __init__(self):
        self.enabled = REDIS_ENABLED
        self.client = None
        
        if self.enabled:
            try:
                self.client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Проверяем подключение
                self.client.ping()
                logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                logger.warning("Redis cache disabled, falling back to no-cache mode")
                self.enabled = False
                self.client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кеша"""
        if not self.enabled or not self.client:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Error getting from cache: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Сохранить значение в кеш"""
        if not self.enabled or not self.client:
            return False
        
        try:
            ttl = ttl or CACHE_TTL
            serialized = json.dumps(value, default=str)
            self.client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Удалить значение из кеша"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Удалить все ключи по паттерну"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cache CLEAR: {pattern} ({deleted} keys)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern: {e}")
            return 0
    
    def flush_all(self) -> bool:
        """Очистить весь кеш"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.info("Cache FLUSH: all keys deleted")
            return True
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Получить статистику Redis"""
        if not self.enabled or not self.client:
            return {"enabled": False}
        
        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected": True,
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Рассчитать процент попаданий в кеш"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)
    
    def is_healthy(self) -> bool:
        """Проверка работоспособности Redis"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except Exception:
            return False


# Глобальный экземпляр кеша
cache = RedisCache()


# Декоратор для кеширования функций
def cached(key_prefix: str, ttl: Optional[int] = None):
    """
    Декоратор для кеширования результатов функций
    
    Usage:
        @cached(key_prefix="dashboard_data", ttl=300)
        def get_dashboard_data():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Формируем ключ кеша
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Пытаемся получить из кеша
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Вычисляем значение
            result = func(*args, **kwargs)
            
            # Сохраняем в кеш
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
