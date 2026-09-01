import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Look for .env in frozen executable dir, bundled MEIPASS, or workspace dir
if getattr(sys, 'frozen', False):
    exe_env = Path(sys.executable).parent / ".env"
    meipass_env = Path(sys._MEIPASS) / ".env"
    if exe_env.exists():
        load_dotenv(exe_env)
    elif meipass_env.exists():
        load_dotenv(meipass_env)
    else:
        load_dotenv()
else:
    load_dotenv()

# We only need one global client instance for the app
_supabase = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _supabase = create_client(url, key)
    return _supabase

def init_db():
    # In Supabase, the schema is managed remotely. We just ensure we can connect.
    # If the .env is missing or invalid, get_supabase() will raise an error early.
    get_supabase()
