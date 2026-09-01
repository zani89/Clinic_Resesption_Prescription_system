import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent))

from db.database import get_supabase

def run_debug():
    print("--- Testing Supabase Connection ---")
    try:
        supabase = get_supabase()
        
        print("Fetching doctors...")
        res = supabase.table("doctors").select("*").execute()
        
        if len(res.data) == 0:
            print("WARNING: The query succeeded but returned 0 rows!")
            print("If you are sure you added data, Row Level Security (RLS) might be enabled on the 'doctors' table blocking the read.")
        else:
            print(f"SUCCESS! Found {len(res.data)} doctors:")
            for d in res.data:
                print(f" - {d}")
                
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    run_debug()
