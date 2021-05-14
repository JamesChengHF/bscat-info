from aiocache import caches, RedisCache
from info.config import db_config

caches.set_config(db_config)
cache = caches.get('redis')
