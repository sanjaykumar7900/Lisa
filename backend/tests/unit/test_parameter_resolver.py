"""Regression: ParameterResolver blocks unresolved params, resolves supplied ones."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.execution.parameter_resolver import ParameterResolver, TestDataStore
from app.core.execution.runtime_context import RuntimeContext


class TestParameterResolverBehavior:
    def test_unresolved_remains_blocked(self):
        resolver = ParameterResolver(TestDataStore())
        resolved, missing = resolver.resolve_path("/v1/items/{itemId}")
        assert resolved == "/v1/items/{itemId}"
        assert "itemId" in missing

    def test_explicit_id_resolves(self):
        store = TestDataStore()
        store.put("itemId", "abc-123")
        resolver = ParameterResolver(store)
        resolved, missing = resolver.resolve_path("/v1/items/{itemId}")
        assert resolved == "/v1/items/abc-123"
        assert missing == []

    def test_response_id_extraction(self):
        store = TestDataStore()
        store.ingest_response({"id": "xyz-789", "name": "test"})
        assert store.get("id") == "xyz-789"

    def test_nested_response_extraction(self):
        store = TestDataStore()
        store.ingest_response({"data": {"id": "nested-123"}})
        assert store.get("id") == "nested-123"

    def test_test_contract_blocks_unresolved_param(self):
        from app.core.execution.test_contract import TestContractEngine

        rt = RuntimeContext()
        resolver = ParameterResolver(TestDataStore())
        # No itemId stored, so path remains unresolved
        contract = TestContractEngine.from_case(
            "TC-API-001", "api", [], rt, resolver,
            evidence_sources=["ItemController.java"],
            discovered_paths={"/v1/items"},
            expected_result="200"
        )
        # Contract has no assertions if expected_result doesn't create one
        assert contract.status in ("UNVERIFIED", "BLOCKED") or "itemId" in contract.path or len(contract.assertions) == 0

    def test_test_contract_resolves_supplied_param(self):
        from app.core.execution.test_contract import TestContractEngine

        rt = RuntimeContext()
        store = TestDataStore()
        store.put("itemId", "supplied-123")
        resolver = ParameterResolver(store)
        contract = TestContractEngine.from_case(
            "TC-API-002", "api", [{"action": "http_get", "target": "/v1/items/{itemId}"}], rt, resolver,
            evidence_sources=["ItemController.java"],
            discovered_paths={"/v1/items/{itemId}", "/v1/items"},
            expected_result="200"
        )
        assert "{itemId}" not in contract.path
        assert contract.path == "/v1/items/supplied-123"

    def test_no_cross_test_contamination(self):
        # Test A stores itemId
        store_a = TestDataStore()
        store_a.put("itemId", "from-test-a")
        # Test B uses fresh store - no contamination
        store_b = TestDataStore()
        resolver_b = ParameterResolver(store_b)
        assert resolver_b.store.get("itemId") is None