import asyncio
from ..agents.security_agent import SecurityAgent
from ..agents.perf_agent import PerfAgent
from ..agents.mobile_agent import MobileAgent
from ..agents.ci_agent import CIAgent

class Orchestrator:
    async def run_all(self, repo_path: str):
        # Parallel, lightweight, independent failure per agent
        results = await asyncio.gather(
            SecurityAgent().run(repo_path),
            PerfAgent().run(repo_path),
            MobileAgent().run(repo_path),
            CIAgent().run(repo_path),
            return_exceptions=True
        )
        return results
