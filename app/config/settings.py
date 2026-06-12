from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Telegram
    telegram_token: SecretStr

    # Supabase
    supabase_url: str
    supabase_service_key: SecretStr
    supabase_jwt_secret: SecretStr

    # DashScope (Qwen-Audio + Qwen Instruct)
    dashscope_api_key: SecretStr
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com"
    qwen_audio_model: str = "qwen3-asr-flash"
    qwen_instruct_model: str = "qwen-flash"

    # Alibaba Cloud OSS
    oss_access_key_id: str = ""
    oss_access_key_secret: SecretStr = SecretStr("")
    oss_bucket_name: str = ""
    oss_endpoint: str = ""

    model_config = SettingsConfigDict(
        env_file="app/config/.env",  # resolved relative to the project root (CWD)
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()