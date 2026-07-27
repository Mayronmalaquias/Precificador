from flask_caching import Cache

from app.config import Config


cache = Cache(config={"CACHE_TYPE": Config.CACHE_TYPE})
