from dataclasses import dataclass
from db.database import get_supabase

@dataclass
class Patient:
    id: int
    contact_number: str
    name: str
    gender: str
    dob: str | None
    age: int | None
    created_at: str | None = None

def find_by_contact(contact_number: str) -> list[Patient]:
    supabase = get_supabase()
    response = supabase.table("patients").select("*").eq("contact_number", contact_number).execute()
    return [Patient(**r) for r in response.data]

def create_patient(contact_number, name, gender, dob=None, age=None) -> int:
    supabase = get_supabase()
    data = {
        "contact_number": contact_number,
        "name": name,
        "gender": gender,
        "dob": dob,
        "age": age
    }
    response = supabase.table("patients").insert(data).execute()
    if not response.data:
        raise Exception("Failed to insert patient.")
    return response.data[0]["id"]
