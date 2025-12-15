from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request

# Primary expected location
DATA_PATH = Path("/app/data/scenarios.json")


def load_scenarios() -> list[dict[str, Any]]:
    """
    Loads scenarios from JSON.

    Expected file path inside container:
      /app/data/scenarios.json

    Expected JSON format:
    {
      "title": "...",
      "scenarios": [
        {"id":"S01","prompt":"...","primary":"Confidentiality","explanation":"..."}
      ]
    }
    """
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing scenarios file at {DATA_PATH}. "
            f"Ensure labs/lab1-cia-matcher/data/scenarios.json exists in the repo and "
            f"the lab image was rebuilt after updating the Dockerfile."
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    scenarios = raw.get("scenarios", [])
    scenarios = sorted(scenarios, key=lambda s: s.get("id", ""))
    return scenarios


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def match():
        scenarios = load_scenarios()
        return render_template(
            "match.html",
            title="Lab 1 — CIA Triad Scenario Matcher",
            scenarios=scenarios,
            results=None,
            score=None,
            total=None,
        )

    @app.post("/submit")
    def submit():
        scenarios = load_scenarios()
        submitted = dict(request.form)

        score = 0
        results: list[dict[str, Any]] = []

        for s in scenarios:
            sid = s.get("id")
            correct = s.get("primary")
            picked = submitted.get(sid, "")
            ok = picked == correct
            score += 1 if ok else 0

            results.append(
                {
                    "id": sid,
                    "prompt": s.get("prompt", ""),
                    "picked": picked,
                    "correct": correct,
                    "ok": ok,
                    "explanation": s.get("explanation", ""),
                    "secondary": s.get("secondary", []),
                }
            )

        return render_template(
            "match.html",
            title="Lab 1 — CIA Triad Scenario Matcher",
            scenarios=scenarios,
            results=results,
            score=score,
            total=len(scenarios),
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
