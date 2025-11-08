import os
import json
from typing import Optional
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

CHANNEL = "flag_updates"

def get_feature_cache(key: str) -> Optional[dict]:
    data = _redis.get(f"feature:{key}")
    if data:
        try:
            return json.loads(data)
        except Exception:
            return None
    return None

def set_feature_cache(key: str, payload: dict):
    _redis.set(f"feature:{key}", json.dumps(payload))

def delete_feature_cache(key: str):
    _redis.delete(f"feature:{key}")

def publish_update(key: str):
    _redis.publish(CHANNEL, key)
