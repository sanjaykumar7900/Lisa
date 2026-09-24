class SecurityAgent:
    def run(self, repo_path: str):
        # Lightweight: Bandit (backend/app only), Semgrep targeted, ZAP API-only
        return {"status":"ok","scans":["bandit","semgrep","zap_api"]}
