import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert "LISA" in data["service"]

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

@pytest.mark.asyncio
async def test_create_and_list_projects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        payload = {"repo_url": "https://github.com/expressjs/express"}
        res = await client.post("/api/v1/projects", json=payload)
        assert res.status_code == 200
        proj = res.json()
        assert proj["repo_url"] == payload["repo_url"]

        # List projects
        res_list = await client.get("/api/v1/projects")
        assert res_list.status_code == 200
        projects = res_list.json()
        assert len(projects) >= 1

@pytest.mark.asyncio
async def test_list_projects_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/projects?skip=0&limit=1")
        assert res.status_code == 200
        projects = res.json()
        assert isinstance(projects, list)
        assert len(projects) <= 1

@pytest.mark.asyncio
async def test_list_bugs_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/bugs?skip=0&limit=5")
        assert res.status_code == 200
        bugs = res.json()
        assert isinstance(bugs, list)
        assert len(bugs) <= 5

@pytest.mark.asyncio
async def test_list_test_runs_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/test-runs?skip=0&limit=5")
        assert res.status_code == 200
        runs = res.json()
        assert isinstance(runs, list)
        assert len(runs) <= 5

@pytest.mark.asyncio
async def test_404_on_nonexistent_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/projects/nonexistent-id")
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_404_on_nonexistent_run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/test-runs/nonexistent-id")
        assert res.status_code == 404

@pytest.mark.asyncio
async def test_404_on_nonexistent_bug():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/bugs/nonexistent-id")
        assert res.status_code == 404
