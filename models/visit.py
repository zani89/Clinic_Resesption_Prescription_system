from dataclasses import dataclass
from db.database import get_supabase

@dataclass
class Visit:
    id: int
    patient_id: int
    doctor_id: int
    visit_date: str
    visit_time: str
    token_number: int
    status: str
    notes: str | None
    created_at: str | None = None

def create_visit(patient_id: int, doctor_id: int, visit_date: str, visit_time: str, notes: str = None) -> int:
    supabase = get_supabase()
    
    # Generate token number
    response = supabase.table("visits").select("id", count="exact").eq("doctor_id", doctor_id).eq("visit_date", visit_date).execute()
    token_number = response.count + 1 if response.count is not None else 1
    
    data = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "visit_date": visit_date,
        "visit_time": visit_time,
        "token_number": token_number,
        "notes": notes
    }
    
    insert_resp = supabase.table("visits").insert(data).execute()
    if not insert_resp.data:
        raise Exception("Failed to create visit.")
    return insert_resp.data[0]["id"]

def get_visit_stats(start_date: str, end_date: str, doctor_id: int = None):
    supabase = get_supabase()
    
    req = supabase.table("visits").select("doctor_id, doctors(name, specialization)").gte("visit_date", start_date).lte("visit_date", end_date)
    if doctor_id is not None:
        req = req.eq("doctor_id", doctor_id)
        
    response = req.execute()
    
    # Aggregate in Python
    stats = {}
    for v in response.data:
        d_id = v["doctor_id"]
        doctor_info = v.get("doctors")
        if not doctor_info:
            continue
            
        if d_id not in stats:
            stats[d_id] = {
                "name": doctor_info.get("name", "Unknown"),
                "specialization": doctor_info.get("specialization", "Unknown"),
                "total": 0
            }
        stats[d_id]["total"] += 1
        
    result = list(stats.values())
    result.sort(key=lambda x: x["total"], reverse=True)
    return result
