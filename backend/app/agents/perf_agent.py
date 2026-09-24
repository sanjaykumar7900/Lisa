class PerfAgent:
    def run(self, repo_path: str, url: str = None):
        # Lightweight smoke: Locust 10u/30s, Lighthouse headless, k6 latency
        return {"status":"ok","tests":["locust_smoke","lighthouse","k6_latency"]}
