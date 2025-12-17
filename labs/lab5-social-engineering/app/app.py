from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request

DATA_PATH = Path("/app/data/scenarios.json")


def load_scenarios() -> dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Missing scenarios file at {DATA_PATH}. Ensure labs/lab5-social-engineering/data/scenarios.json "
            f"exists in the repo and the lab image was rebuilt."
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        data = load_scenarios()
        scenarios = data.get("scenarios", [])
        scenarios = sorted(scenarios, key=lambda s: s.get("id", ""))
        return render_template(
            "analyze.html",
            title=data.get("title", "Lab 5 — Social Engineering Analysis"),
            tagline=data.get("tagline", ""),
            scenarios=scenarios,
            results=None,
            summary=None,
            technique_options=data.get("technique_options", []),
            lever_options=data.get("lever_options", []),
            attacker_goal_options=data.get("attacker_goal_options", []),
            shortcut_options=data.get("shortcut_options", []),
            response_options=data.get("response_options", []),
            teaching_guardrail_options=data.get("teaching_guardrail_options", []),
        )

    @app.post("/submit")
    def submit():
        data = load_scenarios()
        scenarios = data.get("scenarios", [])
        scenarios = sorted(scenarios, key=lambda s: s.get("id", ""))

        submitted = dict(request.form)

        results: list[dict[str, Any]] = []
        matched = {"technique": 0, "lever": 0, "goal": 0}
        total = len(scenarios)

        for s in scenarios:
            sid = s.get("id")
            # single-choice fields
            picked_technique = submitted.get(f"{sid}__technique", "")
            picked_lever = submitted.get(f"{sid}__lever", "")
            picked_goal = submitted.get(f"{sid}__goal", "")
            picked_response = submitted.get(f"{sid}__response", "")

            # multi-choice fields
            picked_shortcuts = request.form.getlist(f"{sid}__shortcuts")
            picked_guardrails = request.form.getlist(f"{sid}__guardrails")

            correct_technique = s.get("answers", {}).get("technique", "")
            correct_lever = s.get("answers", {}).get("lever", "")
            correct_goal = s.get("answers", {}).get("attacker_goal", "")

            ok_technique = picked_technique == correct_technique
            ok_lever = picked_lever == correct_lever
            ok_goal = picked_goal == correct_goal

            matched["technique"] += 1 if ok_technique else 0
            matched["lever"] += 1 if ok_lever else 0
            matched["goal"] += 1 if ok_goal else 0

            # For multi-select, we don’t treat as “right/wrong”; we show overlap to keep it non-gamified.
            correct_shortcuts = s.get("answers", {}).get("shortcuts", [])
            correct_guardrails = s.get("answers", {}).get("teaching_guardrails", [])

            overlap_shortcuts = sorted(set(picked_shortcuts).intersection(set(correct_shortcuts)))
            overlap_guardrails = sorted(set(picked_guardrails).intersection(set(correct_guardrails)))

            results.append(
                {
                    "id": sid,
                    "channel": s.get("channel", ""),
                    "artifact": s.get("artifact", ""),
                    "notes": s.get("notes", ""),
                    "focus": s.get("focus", {}),
                    "picked": {
                        "technique": picked_technique,
                        "lever": picked_lever,
                        "goal": picked_goal,
                        "response": picked_response,
                        "shortcuts": picked_shortcuts,
                        "guardrails": picked_guardrails,
                    },
                    "answers": s.get("answers", {}),
                    "ok": {
                        "technique": ok_technique,
                        "lever": ok_lever,
                        "goal": ok_goal,
                    },
                    "overlap": {
                        "shortcuts": overlap_shortcuts,
                        "guardrails": overlap_guardrails,
                    },
                }
            )

        summary = {
            "total": total,
            "matched": matched,
            "framing": data.get("result_framing", ""),
        }

        return render_template(
            "analyze.html",
            title=data.get("title", "Lab 5 — Social Engineering Analysis"),
            tagline=data.get("tagline", ""),
            scenarios=scenarios,
            results=results,
            summary=summary,
            technique_options=data.get("technique_options", []),
            lever_options=data.get("lever_options", []),
            attacker_goal_options=data.get("attacker_goal_options", []),
            shortcut_options=data.get("shortcut_options", []),
            response_options=data.get("response_options", []),
            teaching_guardrail_options=data.get("teaching_guardrail_options", []),
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
