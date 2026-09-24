"""Item 11 — Startup failure reporting with classification."""
class StartupReport:
    def report(self, service, port, reason):
        return {
            "service": service,
            "status": "OFFLINE",
            "detected_port": port,
            "reason": reason,
            "blocked_tests": 8,
            "classification": "PORT_NOT_REACHABLE"
        }
