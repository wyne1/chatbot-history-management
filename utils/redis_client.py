# utils/redis_client.py

import redis
from config import REDIS_HOST, REDIS_PORT

def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)