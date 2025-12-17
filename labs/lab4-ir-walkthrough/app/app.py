from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from flask import Flask, render_template, request

DATA_PATH = Path("/app/data/incident.json")


def load_incident() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing incident file at {DATA_PATH}. Rebuild the lab4 image.")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_url_path="/static",
        static_folder="static",
        template_folder="templates",
    )

    @app.get("/")
    def index():
        incident = load_incident()
        instructor = request.args.get("instructor", "").strip().lower() in ("1", "true", "yes", "on")
        return render_template("index.html", incident=incident, instructor=instructor)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
