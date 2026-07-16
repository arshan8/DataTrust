import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    LLM_URL = os.getenv("LLM_URL", "http://10.10.3.2:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")

    MONGODB_URI = os.getenv("MONGODB_URI", "")

    ENV = os.getenv("ENV", "development")
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")
    GITHUB_REPO = os.getenv("GITHUB_REPO", "")
    GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

    CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "")
    CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL", "")
    CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")
    CONFLUENCE_SPACE_KEY = os.getenv("CONFLUENCE_SPACE_KEY", "")

    GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    GOOGLE_DRIVE_HR_L1_FOLDER_ID = os.getenv("GOOGLE_DRIVE_HR_L1_FOLDER_ID", "")
    GOOGLE_DRIVE_HR_L2_FOLDER_ID = os.getenv("GOOGLE_DRIVE_HR_L2_FOLDER_ID", "")
    GOOGLE_DRIVE_HR_L3_FOLDER_ID = os.getenv("GOOGLE_DRIVE_HR_L3_FOLDER_ID", "")

    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")
    AUTH0_ISSUER = os.getenv("AUTH0_ISSUER", "")
    
settings = Settings()
