from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, render_template, request

EVENTS_PATH = Path("/app/data/events.json")


def load_events() -> Dict[str, Any]:
    if not EVENTS_PATH.exists():
        raise FileNotFoundError(
            f"Missing events file at {EVENTS_PATH}. Rebuild the lab3 image."
        )
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_app() -> Flask:
    # Be explicit so static/templates always resolve correctly in Docker.
    app = Flask(
        __name__,
        static_url_path="/static",
        static_folder="static",
        template_folder="templates",
    )

    @app.get("/")
    def index():
        payload = load_events()
        instructor = request.args.get("instructor", "").strip().lower() in ("1", "true", "yes", "on")
        title = payload.get("title", "Lab 3 — Threat Detection Workflow: Signal vs Noise")
        scenario = payload.get("scenario", {})
        events: List[Dict[str, Any]] = payload.get("events", [])

        return render_template(
            "index.html",
            title=title,
            scenario=scenario,
            events=events,
            instructor=instructor,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
