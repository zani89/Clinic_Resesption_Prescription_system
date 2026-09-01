from dataclasses import dataclass
from db.database import get_supabase

@dataclass
class Doctor:
    id: int
    name: str
    specialization: str
    status: str

def search_doctors(query: str = "", specialization: str = "") -> list[Doctor]:
    supabase = get_supabase()
    
    req = supabase.table("doctors").select("id, name, specialization, status")
    if query:
        req = req.ilike("name", f"%{query}%")
    if specialization:
        req = req.eq("specialization", specialization)
        
    response = req.execute()
    return [Doctor(id=r["id"], name=r["name"], specialization=r.get("specialization", ""), status=r.get("status", "active")) for r in response.data]

def get_specializations() -> list[str]:
    supabase = get_supabase()
    response = supabase.table("doctors").select("specialization").eq("status", "active").execute()
    specs = set([r['specialization'] for r in response.data if r.get('specialization')])
    return sorted(list(specs))
