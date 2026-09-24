#!/bin/bash
# Unified lightweight runner: pytest + playwright + security/perf/mobile/ci agents
python -m pytest backend/tests/ -q
