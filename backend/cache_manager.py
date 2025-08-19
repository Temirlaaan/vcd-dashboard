# import redis
# import json
# import hashlib
# import logging
# from typing import Any, Optional, Dict, List
# from datetime import datetime, timedelta
# import pickle

# logger = logging.getLogger(__name__)

# class CacheManager:
#     """Улучшенный менеджер кэширования с поддержкой TTL и инвалидации"""
    
#     def __init__(self, redis_url: str = None, redis_password: str = None):
#         """
#         Инициализация менеджера кэширования
        
#         Args:
#             redis_url: URL для подключения к Redis
#             redis_password: Пароль для Redis
#         """
#         self.redis_client = None
#         self.local_cache = {}  # Fallback на локальный кэш
#         self.cache_stats = {
#             'hits': 0,
#             'misses': 0,
#             'errors': 0
#         }
        
#         if redis_url:
#             try:
#                 self.redis_client = redis.Redis(
#                     host=redis_url.split(':')[0],
#                     port=int(redis_url.split(':')[1]) if ':' in redis_url else 6379,
#                     password=redis_password,
#                     decode_responses=False,  # Для поддержки pickle
#                     socket_keepalive=True,
#                     socket_keepalive_options={
#                         1: 1,  # TCP_KEEPIDLE
#                         2: 3,  # TCP_KEEPINTVL
#                         3: 5   # TCP_KEEPCNT
#                     }
#                 )
#                 # Проверка подключения
#                 self.redis_client.ping()
#                 logger.info("Connected to Redis cache")
#             except Exception as e:
#                 logger.warning(f"Failed to connect to Redis: {e}. Using local cache.")
#                 self.redis_client = None
    
#     def _generate_key(self, prefix: str, params: Dict) -> str:
#         """Генерация уникального ключа для кэша"""
#         # Сортируем параметры для консистентности
#         sorted_params = json.dumps(params, sort_keys=True)
#         hash_digest = hashlib.md5(sorted_params.encode()).hexdigest()[:8]
#         return f"{prefix}:{hash_digest}"
    
#     def get(self, key: str, default: Any = None) -> Any:
#         """
#         Получить значение из кэша
        
#         Args:
#             key: Ключ кэша
#             default: Значение по умолчанию
        
#         Returns:
#             Закэшированное значение или default
#         """
#         try:
#             if self.redis_client:
#                 value = self.redis_client.get(key)
#                 if key in self.local_cache:
#                     del self.local_cache[key]
#                     return True
#                 return False
                
#         except Exception as e:
#             logger.error(f"Cache delete error for key {key}: {e}")
#             return False
    
#     def delete_pattern(self, pattern: str) -> int:
#         """
#         Удалить все ключи по паттерну
        
#         Args:
#             pattern: Паттерн для поиска ключей (например, "vcd:*")
        
#         Returns:
#             Количество удаленных ключей
#         """
#         try:
#             if self.redis_client:
#                 keys = self.redis_client.keys(pattern)
#                 if keys:
#                     return self.redis_client.delete(*keys)
#             else:
#                 # Локальный кэш
#                 keys_to_delete = [k for k in self.local_cache.keys() if pattern.replace('*', '') in k]
#                 for key in keys_to_delete:
#                     del self.local_cache[key]
#                 return len(keys_to_delete)
                
#         except Exception as e:
#             logger.error(f"Cache delete pattern error for {pattern}: {e}")
#             return 0
    
#     def invalidate_cloud_cache(self, cloud_name: str):
#         """Инвалидировать весь кэш для конкретного облака"""
#         pattern = f"vcd:{cloud_name}:*"
#         deleted = self.delete_pattern(pattern)
#         logger.info(f"Invalidated {deleted} cache entries for cloud {cloud_name}")
    
#     def _cleanup_local_cache(self):
#         """Очистка истекших записей из локального кэша"""
#         now = datetime.now()
#         expired_keys = [k for k, v in self.local_cache.items() if v['expires_at'] <= now]
#         for key in expired_keys:
#             del self.local_cache[key]
        
#         # Ограничение размера кэша
#         if len(self.local_cache) > 1000:
#             # Удаляем самые старые записи
#             sorted_items = sorted(self.local_cache.items(), key=lambda x: x[1]['expires_at'])
#             for key, _ in sorted_items[:100]:
#                 del self.local_cache[key]
    
#     def get_stats(self) -> Dict:
#         """Получить статистику кэша"""
#         total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
#         hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
#         stats = {
#             'hits': self.cache_stats['hits'],
#             'misses': self.cache_stats['misses'],
#             'errors': self.cache_stats['errors'],
#             'hit_rate': round(hit_rate, 2),
#             'backend': 'redis' if self.redis_client else 'local',
#             'local_cache_size': len(self.local_cache) if not self.redis_client else 0
#         }
        
#         if self.redis_client:
#             try:
#                 info = self.redis_client.info('memory')
#                 stats['redis_memory_used'] = info.get('used_memory_human', 'N/A')
#                 stats['redis_keys'] = self.redis_client.dbsize()
#             except:
#                 pass
        
#         return stats
    
#     def cache_result(self, key_prefix: str, ttl: int = 300):
#         """
#         Декоратор для кэширования результатов функций
        
#         Usage:
#             @cache_manager.cache_result('ip_pools', ttl=600)
#             def get_ip_pools(cloud_name):
#                 # expensive operation
#                 return pools
#         """
#         def decorator(func):
#             def wrapper(*args, **kwargs):
#                 # Генерируем ключ на основе аргументов функции
#                 cache_key = self._generate_key(
#                     f"{key_prefix}:{func.__name__}",
#                     {'args': args, 'kwargs': kwargs}
#                 )
                
#                 # Пробуем получить из кэша
#                 cached_value = self.get(cache_key)
#                 if cached_value is not None:
#                     logger.debug(f"Cache hit for {func.__name__}")
#                     return cached_value
                
#                 # Выполняем функцию
#                 result = func(*args, **kwargs)
                
#                 # Сохраняем в кэш
#                 self.set(cache_key, result, ttl)
                
#                 return result
#             return wrapper
#         return decorator value:
#                     self.cache_stats['hits'] += 1
#                     # Пробуем десериализовать как JSON, затем как pickle
#                     try:
#                         return json.loads(value)
#                     except:
#                         return pickle.loads(value)
#             else:
#                 # Локальный кэш
#                 if key in self.local_cache:
#                     entry = self.local_cache[key]
#                     if entry['expires_at'] > datetime.now():
#                         self.cache_stats['hits'] += 1
#                         return entry['value']
#                     else:
#                         del self.local_cache[key]
            
#             self.cache_stats['misses'] += 1
#             return default
            
#         except Exception as e:
#             logger.error(f"Cache get error for key {key}: {e}")
#             self.cache_stats['errors'] += 1
#             return default
    
#     def set(self, key: str, value: Any, ttl: int = 300) -> bool:
#         """
#         Сохранить значение в кэш
        
#         Args:
#             key: Ключ кэша
#             value: Значение для сохранения
#             ttl: Время жизни в секундах
        
#         Returns:
#             True если успешно, False иначе
#         """
#         try:
#             if self.redis_client:
#                 # Пробуем сериализовать как JSON, иначе используем pickle
#                 try:
#                     serialized = json.dumps(value, default=str)
#                 except:
#                     serialized = pickle.dumps(value)
                
#                 self.redis_client.setex(key, ttl, serialized)
#                 return True
#             else:
#                 # Локальный кэш
#                 self.local_cache[key] = {
#                     'value': value,
#                     'expires_at': datetime.now() + timedelta(seconds=ttl)
#                 }
#                 # Очистка старых записей
#                 self._cleanup_local_cache()
#                 return True
                
#         except Exception as e:
#             logger.error(f"Cache set error for key {key}: {e}")
#             self.cache_stats['errors'] += 1
#             return False
    
#     def delete(self, key: str) -> bool:
#         """Удалить значение из кэша"""
#         try:
#             if self.redis_client:
#                 return self.redis_client.delete(key) > 0
#             else:
#                 if