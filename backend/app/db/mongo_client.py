from pymongo import MongoClient
from app.core.config import settings

mongo_client = MongoClient(settings.MONGODB_URI)
mongo_db = mongo_client["datatrust"]

audit_logs = mongo_db["audit_logs"]
prompt_logs = mongo_db["prompt_logs"]
system_events = mongo_db["system_events"]