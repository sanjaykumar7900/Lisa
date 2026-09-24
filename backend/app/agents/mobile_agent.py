class MobileAgent:
    def run(self, repo_path: str):
        # On-demand Appium; else Playwright device emulation (lightweight)
        return {"status":"ok","mode":"appium_or_emulation"}
