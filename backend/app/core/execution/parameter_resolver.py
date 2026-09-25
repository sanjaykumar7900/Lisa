"""Resolve path/query/body parameters from runtime test data and prior responses."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

UNRESOLVED = re.compile(r"\{([^{}/]+)\}")


class TestDataStore:
    def __init__(self) -> None:
        self.values: Dict[str, Any] = {}

    def put(self, key: str, value: Any) -> None:
        if key and value is not None:
            self.values[str(key)] = value
            lowered = str(key).lower()
            if lowered.endswith("id") or lowered == "id":
                self.values.setdefault("id", value)
                self.values.setdefault("itemId", value)
                self.values.setdefault("item_id", value)

    def ingest_response(self, payload: Any) -> None:
        data = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                return
        if isinstance(data, dict):
            for key in ("id", "itemId", "item_id", "uuid", "token", "access_token", "csrfToken"):
                if key in data and data[key] not in (None, ""):
                    self.put(key, data[key])
            nested = data.get("data") if isinstance(data.get("data"), dict) else None
            if nested:
                self.ingest_response(nested)

    def get(self, key: str) -> Any:
        if key in self.values:
            return self.values[key]
        return self.values.get(key[0].lower() + key[1:]) if key else None


class ParameterResolver:
    def __init__(self, store: Optional[TestDataStore] = None) -> None:
        self.store = store or TestDataStore()

    def unresolved_tokens(self, text: str) -> List[str]:
        return UNRESOLVED.findall(text or "")

    def resolve_path(self, path: str) -> Tuple[str, List[str]]:
        missing: List[str] = []

        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            value = self.store.get(name)
            if value is None:
                missing.append(name)
                return match.group(0)
            return str(value)

        resolved = UNRESOLVED.sub(repl, path or "")
        return resolved, missing

    def resolve_value(self, value: Any) -> Any:
        if isinstance(value, str):
            resolved, missing = self.resolve_path(value)
            return resolved if not missing else value
        if isinstance(value, dict):
            return {k: self.resolve_value(v) for k, v in value.items()}
        return value
