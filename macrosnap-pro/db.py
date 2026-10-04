import datetime
import os
import streamlit as st
from supabase import create_client, Client
from logger import log_execution_time

def get_supabase_credentials():
    """Fallback logic to support both Streamlit secrets and standard ENV vars."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    return url, key

# Cache the client for Streamlit, but allow standard instantiation for FastAPI
try:
    @st.cache_resource
    def get_supabase_client() -> Client:
        url, key = get_supabase_credentials()
        return create_client(url, key)
except ImportError:
    def get_supabase_client() -> Client:
        url, key = get_supabase_credentials()
        return create_client(url, key)

@log_execution_time
def get_user_by_whatsapp(whatsapp_number: str):
    db = get_supabase_client()
    res = db.table("profiles").select("*").eq("whatsapp_number", whatsapp_number).execute()
    return res.data[0] if res.data else None

@log_execution_time
def create_user_profile(profile_data: dict = None, **kwargs):
    """Creates or updates a user profile in Supabase."""
    data = dict(profile_data) if profile_data else {}
    data.update(kwargs)

    # ✅ Fallbacks for required database constraints
    if "name" not in data or not data["name"]:
        data["name"] = "New User"
        
    if "tdee" not in data or not data["tdee"]:
        data["tdee"] = 2000  # Provide a standard default calorie goal

    # If 'id' is empty, None, or blank, remove it so Supabase
    # can automatically generate a UUID using gen_random_uuid()
    if "id" in data and not data["id"]:
        data.pop("id", None)

    db = get_supabase_client()
    res = db.table("profiles").upsert(data, on_conflict="whatsapp_number").execute()
    return res.data[0] if res.data else None
@log_execution_time
def get_daily_logs(user_id: str, date_str: str = None):
    if not date_str:
        date_str = str(datetime.date.today())
    db = get_supabase_client()
    res = db.table("meal_logs").select("*").eq("user_id", user_id).eq("log_date", date_str).execute()
    return res.data or []

@log_execution_time
def log_meal_db(meal_data: dict):
    """Inserts a new meal log into the Supabase database."""
    db = get_supabase_client()
    res = db.table("meal_logs").insert(meal_data).execute()
    return res.data[0] if res.data else None
