"""Configuration settings for data catalog service"""
from pydantic import BaseSettings

class Settings(BaseSettings):
    pass
    
def get_settings():
    return Settings()