from pymongo import MongoClient
from app.core.config import settings

_client = None
_db = None


def get_mongo_db():
    global _client, _db

    if _db is not None:
        return _db

    if not settings.MONGODB_URI:
        raise ValueError("MONGODB_URI is not configured")

    _client = MongoClient(settings.MONGODB_URI)

    # If your URI already includes db name, this works.
    # Otherwise change "datatrust" to your actual DB name.
    # _db = _client.get_default_database()
    _db = _client["datatrust"]

    return _db