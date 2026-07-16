import psycopg
from app.core.config import settings


def get_pg_connection():
    if not settings.SUPABASE_DB_URL:
        raise ValueError("SUPABASE_DB_URL is not configured")
    return psycopg.connect(settings.SUPABASE_DB_URL)