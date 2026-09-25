"""Regression: TargetResolver must reject placeholder/invented/unresolved targets."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.execution.target_resolver import TargetResolver, TargetResolution
from app.core.execution.runtime_context import RuntimeContext


class TestTargetResolver:
    def _runtime(self, base_url="http://127.0.0.1:9001"):
        rt = RuntimeContext()
        rt.backend_base_url = base_url
        rt.api_base_url = base_url
        rt.real_target_available = True
        rt.services = [
            {"name": "backend", "type": "backend", "host": "127.0.0.1",
             "port": 9001, "base_url": base_url, "status": "READY"}
        ]
        return rt

    def test_example_com_rejected(self):
        rt = self._runtime()
        res = TargetResolver.resolve("https://example.com/something", rt)
        assert res.accepted is False
        assert "example" in res.reason.lower() or "placeholder" in res.reason.lower()

    def test_unresolved_path_param_rejected(self):
        rt = self._runtime()
        res = TargetResolver.resolve("/v1/items/{itemId}", rt)
        assert res.accepted is False
        assert "unresolved" in res.reason.lower()

    def test_undocumented_health_rejected(self):
        rt = self._runtime()
        # No /api/health in discovered paths
        res = TargetResolver.resolve("/api/health", rt, discovered_paths=set())
        assert res.accepted is False

    def test_valid_discovered_endpoint_accepted(self):
        rt = self._runtime()
        res = TargetResolver.resolve(
            "/v1/items", rt, discovered_paths={"/v1/items"}
        )
        assert res.accepted is True
        assert res.url.startswith("http://127.0.0.1:9001")

    def test_hardcoded_port_independence(self):
        rt = self._runtime(base_url="http://127.0.0.1:19002")
        res = TargetResolver.resolve(
            "/v1/items", rt, discovered_paths={"/v1/items"}
        )
        assert res.accepted is True
        assert res.url == "http://127.0.0.1:19002/v1/items"
        assert res.url.endswith("19002/v1/items")
        assert ":8080" not in res.url
        assert ":9001/v1/items" not in res.url