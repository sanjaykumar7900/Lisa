from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel

class LLMProvider(ABC):
    """Abstract interface for LLM providers in LISA."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        """Generates plain text response from LLM."""
        pass

    @abstractmethod
    async def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """Generates structured Pydantic object validated output."""
        pass

    @abstractmethod
    async def analyze(self, context: Dict[str, Any], prompt: str) -> str:
        """Performs specialized context analysis (e.g. failure analysis, code analysis)."""
        pass
