"""Service dependency graph used to order startup and block dependents."""

from __future__ import annotations

from typing import Any, Dict, List


class ServiceTopology:
    @staticmethod
    def build(services: List[Dict[str, Any]], database: Dict[str, Any] | None = None) -> Dict[str, Any]:
        nodes = list(services)
        if database and database.get("type") not in (None, "Not detected", ""):
            if not any(str(n.get("type") or "").lower() in {"database", "postgres", "postgresql", "mysql", "mongodb", "sqlite"} for n in nodes):
                nodes.append(
                    {
                        "name": str(database.get("name") or database.get("type") or "database"),
                        "type": "database",
                        "technology": database.get("type"),
                        "dependencies": [],
                        "evidence": database.get("evidence") or [],
                        "confidence": database.get("confidence") or 0.5,
                    }
                )

        names = {str(n.get("name") or "").lower(): n for n in nodes}

        def ensure_dep(src: str, dst: str) -> None:
            node = names.get(src)
            target = names.get(dst)
            if node and target:
                deps = list(node.get("dependencies") or [])
                if dst not in deps:
                    deps.append(dst)
                node["dependencies"] = deps

        if "frontend" in names and "backend" in names:
            ensure_dep("frontend", "backend")
        if "backend" in names:
            db_name = next((n.get("name") for n in nodes if str(n.get("type")).lower() == "database"), None)
            if db_name:
                ensure_dep("backend", str(db_name))
        if "gateway" in names and "backend" in names:
            ensure_dep("gateway", "backend")
        if "frontend" in names and "gateway" in names:
            ensure_dep("frontend", "gateway")

        return {"nodes": nodes, "edges": ServiceTopology._edges(nodes)}

    @staticmethod
    def _edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        edges = []
        for node in nodes:
            for dep in node.get("dependencies") or []:
                edges.append({"from": node.get("name"), "to": dep})
        return edges

    @staticmethod
    def blocked_dependents(nodes: List[Dict[str, Any]], unavailable: str) -> List[str]:
        blocked = {unavailable}
        changed = True
        while changed:
            changed = False
            for node in nodes:
                deps = set(node.get("dependencies") or [])
                if deps & blocked and node.get("name") not in blocked:
                    blocked.add(str(node.get("name")))
                    changed = True
        blocked.discard(unavailable)
        return sorted(blocked)
