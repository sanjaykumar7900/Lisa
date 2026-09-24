import logging
from app.core.config import settings
from app.services.llm.base import LLMProvider
from app.services.llm.nvidia_provider import NvidiaProvider
from app.services.llm.fallback_provider import FallbackProvider

logger = logging.getLogger(__name__)

def get_llm_provider(force_fallback: bool = False) -> LLMProvider:
    """
    Factory function returning the active LLM Provider.
    Defaults to NvidiaProvider if NVIDIA_API_KEY is configured,
    otherwise gracefully falls back to FallbackProvider.
    """
    if force_fallback or not settings.NVIDIA_API_KEY:
        if not settings.NVIDIA_API_KEY and not force_fallback:
            logger.info("NVIDIA_API_KEY is not set. Using LISA Fallback LLM Provider.")
        return FallbackProvider()
    
    try:
        return NvidiaProvider()
    except Exception as e:
        logger.warning(f"Failed to initialize NvidiaProvider ({e}). Using FallbackProvider.")
        return FallbackProvider()
