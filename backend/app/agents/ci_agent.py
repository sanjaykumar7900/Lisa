class CIAgent:
    def run(self, repo_path: str):
        # Single workflow file + artifact upload; triggers LISA on PR
        return {"status":"ok","pipeline":"github_actions"}
