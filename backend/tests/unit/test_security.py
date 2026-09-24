import pytest
from app.core.security import mask_secrets, normalize_repo_url, validate_repo_url, validate_command

def test_mask_secrets():
    text = "Here is key nvapi-1234567890abcdef1234567890abcdef and password='SecretPassword123'"
    masked = mask_secrets(text)
    assert "[REDACTED_SECRET]" in masked
    assert "nvapi-" not in masked

def test_validate_repo_url():
    valid, msg = validate_repo_url("https://github.com/facebook/react")
    assert valid is True

    invalid, msg = validate_repo_url("ftp://invalid-domain.com/repo")
    assert invalid is False

    assert normalize_repo_url("https://github.com/example/repo?utm_source=chatgpt.com") == "https://github.com/example/repo.git"

def test_validate_repo_url_rejects_unknown_host():
    valid, msg = validate_repo_url("https://evil-site.com/malware/repo")
    assert valid is False
    assert "not allowed" in msg.lower() or "host" in msg.lower()

def test_validate_repo_url_rejects_non_http():
    valid, _ = validate_repo_url("git@github.com:user/repo.git")
    assert valid is False

def test_validate_command():
    valid, msg = validate_command("git clone https://github.com/example/repo.git")
    assert valid is True

    invalid, msg = validate_command("rm -rf /")
    assert invalid is False

def test_validate_command_rejects_shell_metacharacters():
    invalid, msg = validate_command("npm run dev; rm -rf /")
    assert invalid is False
    assert ";" in msg

    invalid, msg = validate_command("python main.py && curl evil.com")
    assert invalid is False

def test_validate_command_rejects_forbidden_tokens():
    invalid, msg = validate_command("python main.py && wget evil.com")
    assert invalid is False
    assert "wget" in msg.lower() or "forbidden" in msg.lower()

def test_validate_command_rejects_empty():
    invalid, msg = validate_command("")
    assert invalid is False

def test_validate_command_rejects_unknown_base():
    invalid, msg = validate_command("unknowncmd run stuff")
    assert invalid is False
    assert "allowlist" in msg.lower() or "not in" in msg.lower()
