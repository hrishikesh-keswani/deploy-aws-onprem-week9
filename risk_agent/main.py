"""Run the risk agent once and print the risk JSON."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from risk_agent.agent import score_case

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "fixtures" / "priya_shah.json"


def main() -> int:
    provider = os.environ.get("LLM_PROVIDER", "bedrock").strip().lower()
    fixture_path = Path(os.environ.get("FIXTURE_PATH", str(DEFAULT_FIXTURE)))
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        client = _client(provider)
        result = score_case(payload, client)
    except Exception as exc:
        print("risk agent failed: {0}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _client(provider: str):
    if provider == "ollama":
        from risk_agent.llm_ollama import OllamaClient

        return OllamaClient()
    if provider == "bedrock":
        from risk_agent.llm_bedrock import BedrockClient

        return BedrockClient()
    raise ValueError("LLM_PROVIDER must be bedrock or ollama")


if __name__ == "__main__":
    sys.exit(main())
