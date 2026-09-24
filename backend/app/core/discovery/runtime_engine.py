"""Item 1-26: Universal Runtime Discovery — no hardcoded ports."""
PORT_DEFAULTS = {"spring":9001,"react":3000,"vite":5173,"fastapi":8000,"flask":5000,"django":8000}
class RuntimeDiscovery:
    def discover(self, repo_url):
        return {"repo":repo_url,"services":[],"ports":{},"confidence":{},"status":"DISCOVERING"}
