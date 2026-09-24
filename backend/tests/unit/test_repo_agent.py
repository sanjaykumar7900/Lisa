import pytest
from pathlib import Path
from app.services.repo_agent import RepositoryAgent

def test_repo_agent_analysis(tmp_path):
    # Setup mock repo dir with package.json and README
    (tmp_path / "package.json").write_text('{"name": "test-app", "dependencies": {"react": "^18.0.0", "express": "^4.18.0"}, "scripts": {"dev": "vite"}}')
    (tmp_path / "README.md").write_text("# Test App\nA React and Express application.")

    agent = RepositoryAgent(repo_url="https://github.com/example/test", project_id="test_proj_001")
    agent.clone_path = tmp_path

    analysis = agent.analyze()
    assert analysis["frontend"] == "React"
    assert analysis["backend"] == "Express.js"
    assert "npm run dev" in analysis["startup_commands"]
    assert analysis["api_available"] is True


def test_repo_agent_detects_nested_python_project(tmp_path):
    project_dir = tmp_path / "secscan"
    project_dir.mkdir()
    (project_dir / "requirements.txt").write_text("requests\npytest\n")
    (project_dir / "main.py").write_text("print('secscan')")

    agent = RepositoryAgent(repo_url="https://github.com/example/secscan", project_id="test_secscan")
    agent.clone_path = tmp_path

    analysis = agent.analyze()

    assert "Python" in analysis["languages"]
    assert analysis["backend"] == "Python"
    assert analysis["test_framework"] == "pytest"
    assert "python secscan/main.py" in analysis["startup_commands"]
