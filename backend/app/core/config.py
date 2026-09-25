import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    PROJECT_NAME: str = "LISA — Learning & Intelligent Software Assurance"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # LISA Backend Server Configuration
    LISA_BACKEND_PORT: int = int(os.getenv("LISA_BACKEND_PORT", os.getenv("PORT", "8000")))
    LISA_HOST: str = os.getenv("LISA_HOST", "0.0.0.0")

    # Target Application Testing & Runtime Port Discovery Configuration
    TARGET_APPLICATION_PORT: int | None = int(os.getenv("TARGET_APPLICATION_PORT")) if os.getenv("TARGET_APPLICATION_PORT") else None
    TARGET_PORT_RANGE_START: int = int(os.getenv("TARGET_PORT_RANGE_START", "3000"))
    APP_PORT_POLL_INTERVAL: float = float(os.getenv("APP_PORT_POLL_INTERVAL", "0.5"))
    APP_STARTUP_TIMEOUT: float = float(os.getenv("APP_STARTUP_TIMEOUT", "20.0"))  # seconds for target app startup & discovery

    # LLM Settings
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    DEFAULT_LLM_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{(Path(__file__).resolve().parent.parent.parent / 'lisa.db').as_posix()}"
    
    # Execution Limits
    MAX_TEST_STEPS: int = 50
    MAX_TEST_TIME: int = 90  # seconds per test case / session (faster for demo/dev)
    APP_STARTUP_TIMEOUT: float = float(os.getenv("APP_STARTUP_TIMEOUT", "15.0"))  # seconds (faster)
    BROWSER_STEP_TIMEOUT_MS: int = int(os.getenv("BROWSER_STEP_TIMEOUT_MS", "10000"))  # ms per Playwright step
    MAX_REPO_FILES: int = int(os.getenv("MAX_REPO_FILES", "5000"))  # max files to scan
    MAX_REPO_SIZE_MB: int = int(os.getenv("MAX_REPO_SIZE_MB", "500"))  # max clone size
    MAX_EVIDENCE_AGE_DAYS: int = int(os.getenv("MAX_EVIDENCE_AGE_DAYS", "30"))  # evidence retention
    
    # Paths
    EVIDENCE_DIR: Path = BASE_DIR / "runs"
    TEMP_REPO_DIR: Path = BASE_DIR / "temp_repos"
    
    # Security / Allowed Commands
    ALLOWED_COMMANDS: list[str] = [
        "git", "npm", "npx", "node", "python", "python3", "pytest", "pip", "yarn", "pnpm", "go", "cargo",
        "mvn", "mvnw", "mvnw.cmd", "gradle", "gradlew", "gradlew.bat", "uvicorn",
    ]
    LISA_DIAGNOSTIC_FALLBACK: bool = os.getenv("LISA_DIAGNOSTIC_FALLBACK", "").lower() in {"1", "true", "yes"}
    
    # Autonomy Levels
    DEFAULT_AUTONOMY_LEVEL: int = 3  # 0: Manual, 1: Assisted, 2: Automated, 3: Autonomous, 4: Contribution

    # API Key Authentication (optional — if unset, endpoints are open in dev mode)
    LISA_API_KEY: str = os.getenv("LISA_API_KEY", "")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Keep relative .env database URLs from changing the database when launched from another directory.
if settings.DATABASE_URL.startswith("sqlite+aiosqlite:///./"):
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{(settings.BASE_DIR / 'lisa.db').as_posix()}"

# Ensure directories exist
settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_REPO_DIR.mkdir(parents=True, exist_ok=True)
