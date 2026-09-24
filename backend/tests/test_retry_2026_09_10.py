"""
Test case for retry of LISA upgrade (Sept 10 2026)
Tests: middleware fix, /health endpoint, repo fetch, agent modules
"""

import pytest

def test_health_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_agents_exist():
    from app.agents.security_agent import SecurityAgent
    from app.agents.perf_agent import PerfAgent
    from app.agents.mobile_agent import MobileAgent
    from app.agents.ci_agent import CIAgent
    assert SecurityAgent().run(".")
    assert PerfAgent().run(".")
    assert MobileAgent().run(".")
    assert CIAgent().run(".")

def test_repo_url_reachable():
    import urllib.request
    url = "https://github.com/jansabbe/todo-app"
    with urllib.request.urlopen(url, timeout=10) as r:
        assert r.status == 200
