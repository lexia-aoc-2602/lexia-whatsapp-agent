"""
Configuration settings for Lexia WhatsApp Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "Lexia WhatsApp Agent"
    app_version: str = "1.0.0"
    port: int = int(os.getenv("PORT", "8080"))
    environment: str = os.getenv("ENVIRONMENT", "production")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Google Cloud Configuration
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "lexia-platform-488308")
    gcp_region: str = os.getenv("GCP_REGION", "southamerica-east1")
    google_application_credentials: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # Meta WhatsApp Business API
    phone_number_id: str = os.getenv("PHONE_NUMBER_ID", "551528574703551")
    verify_token: str = os.getenv("VERIFY_TOKEN", "lexia-aoc-2602")
    waba_id: str = os.getenv("WABA_ID", "535733579621373")
    whatsapp_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    webhook_url: str = os.getenv(
        "WEBHOOK_URL",
        "https://graph.facebook.com/v21.0/551528574703551/messages"
    )
    
    # ADK Configuration
    adk_model: str = os.getenv("ADK_MODEL", "gemini-2.5-flash")
    adk_agent_name: str = os.getenv("ADK_AGENT_NAME", "lexia_whatsapp_agent")
    
    # Feature Flags
    enable_message_read_status: bool = True
    enable_typing_indicator: bool = True
    enable_message_templates: bool = False
    
    # Timeouts
    message_processing_timeout: int = 30
    webhook_response_timeout: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def validate_required_settings(self) -> bool:
        """Validate that all required settings are configured"""
        required = [
            self.phone_number_id,
            self.verify_token,
            self.waba_id,
            self.whatsapp_access_token,
        ]
        return all(required)

# Create global settings instance
settings = Settings()
