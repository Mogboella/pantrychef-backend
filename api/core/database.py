from supabase import create_client, Client
import os
from api.settings import Settings

settings = Settings()


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
