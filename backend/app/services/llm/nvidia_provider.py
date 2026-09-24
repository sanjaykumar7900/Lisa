import json
import logging
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class NvidiaProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.NVIDIA_API_KEY
        self.model = model or settings.DEFAULT_LLM_MODEL
        self.base_url = settings.NVIDIA_BASE_URL

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is not set.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def generate_structured(
        self, 
        prompt: str, 
        schema_class: Type[BaseModel], 
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        enhanced_system_prompt = (
            (system_prompt or "You are LISA AI QA Architect.") +
            f"\n\nReturn ONLY a valid JSON object matching the following JSON Schema:\n{schema_json}\nDo NOT wrap output in markdown fences or explanations."
        )

        raw_output = await self.generate(prompt=prompt, system_prompt=enhanced_system_prompt, temperature=0.1)
        
        # Clean markdown codeblocks if present
        clean_json = raw_output.strip()
        if clean_json.startswith("```"):
            lines = clean_json.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_json = "\n".join(lines).strip()

        try:
            parsed = json.loads(clean_json)
            return schema_class.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"NvidiaProvider structured validation failed: {e}. Retrying with strict instruction...")
            # Simple 1-step repair attempt
            repair_prompt = f"Fix the following invalid JSON so it conforms strictly to the schema:\n{clean_json}\n\nError: {str(e)}"
            repaired_output = await self.generate(prompt=repair_prompt, system_prompt=enhanced_system_prompt, temperature=0.0)
            clean_repaired = repaired_output.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return schema_class.model_validate(json.loads(clean_repaired))

    async def analyze(self, context: Dict[str, Any], prompt: str) -> str:
        ctx_str = json.dumps(context, indent=2)
        full_prompt = f"Context:\n{ctx_str}\n\nQuestion/Task:\n{prompt}"
        return await self.generate(full_prompt, system_prompt="You are LISA's Failure & Bug Analysis Engine.")
