from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: SecretStr
    # JWT verification (M4): the PWA sends a Supabase access token; we verify it
    # against the asymmetric signing keys (JWKS endpoint derived from
    # supabase_url), never the legacy shared HS256 secret. No secret needed —
    # only public keys. ``aud`` is the claim Supabase puts on access tokens.
    supabase_jwt_aud: str = "authenticated"

    # DashScope (qwen3-asr-flash: speech→text · qwen-flash: text→JSON)
    dashscope_api_key: SecretStr
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com"
    qwen_audio_model: str = "qwen3-asr-flash"
    qwen_instruct_model: str = "qwen-flash"
    # Transport timeout (seconds) for synchronous vendor SDKs run in worker
    # threads (DashScope/Qwen, OSS). Their defaults are high (DashScope 300s,
    # oss2 60s × 3 retries), which leaves a field advisor hanging AND leaks the
    # thread pool until it saturates. A hit fires the underlying requests/aiohttp
    # timeout so the worker thread dies and the error surfaces as a domain error.
    vendor_timeout_seconds: int = 30

    # ITEAF inspection validity (years). An application equipment's inspection
    # is legally valid for this many years (RD 1702/2011: 5 years originally,
    # 3 years for equipment in professional use since 2020-01-01). Past it, the
    # execution flags ``iteaf_warning`` (a non-blocking notice, never a block).
    iteaf_validity_years: int = 3

    # Hackathon self-signup (TEMPORARY — decisions.md). Off by default: the
    # permanent design is admin-only alta of advisors (no self-signup). When ON,
    # the PWA exposes a "Crear cuenta" tab and ``POST /api/bootstrap`` provisions
    # a fresh Supabase user with a demo advisor + seeded holding/plots/equipment
    # so a hackathon judge can try the voice flow immediately. Flip to False (or
    # delete the flag, the endpoint and OnboardingService) to restore the closed
    # login after the event.
    hackathon_signup_enabled: bool = False

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