from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for

from .docker_control import get_running_lab_id, load_labs, start_lab_steps, stop_all_labs_steps

bp = Blueprint("hub", __name__)

# Resolve assessments directory relative to this file to avoid CWD issues
ASSESSMENTS_DIR = (Path(__file__).resolve().parent / "assessments").resolve()


def load_assessment(name: str) -> dict:
    path = (ASSESSMENTS_DIR / f"{name}.json").resolve()
    if not str(path).startswith(str(ASSESSMENTS_DIR)):
        abort(404)
    if not path.exists() or not path.is_file():
        abort(404)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sse(events: Iterator[dict]) -> Response:
    def gen():
        for ev in events:
            payload = json.dumps(ev, ensure_ascii=False)
            # single event channel; JS parses JSON
            yield f"data: {payload}\n\n"

    return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@bp.get("/")
def index():
    labs = load_labs()
    running_lab_id = get_running_lab_id()
    return render_template("index.html", labs=labs, running_lab_id=running_lab_id)


@bp.get("/labs")
def labs_page():
    labs = load_labs()
    running_lab_id = get_running_lab_id()
    return render_template("labs.html", labs=labs, running_lab_id=running_lab_id)


# --- Modal-progress API endpoints (SSE) ---

@bp.get("/api/labs/start/<lab_id>")
def api_labs_start(lab_id: str):
    return _sse(start_lab_steps(lab_id))


@bp.get("/api/labs/stop-all")
def api_labs_stop_all():
    return _sse(stop_all_labs_steps())


# --- Keep these simple routes for non-JS fallback (optional) ---

@bp.post("/labs/stop")
def labs_stop_fallback():
    # Non-modal fallback: best-effort stop, then return to index
    try:
        # consume generator to execute
        for _ in stop_all_labs_steps():
            pass
        flash("Stopped all labs.", "success")
    except Exception as e:
        flash(f"Failed to stop labs: {e}", "error")
    return redirect(url_for("hub.index"))


@bp.get("/assessments")
def assessments_index():
    available = []
    for name in ("pre", "post"):
        p = ASSESSMENTS_DIR / f"{name}.json"
        if p.exists():
            data = load_assessment(name)
            available.append({"name": name, "title": data.get("title", name)})
    return render_template("assessments_index.html", assessments=available)


@bp.get("/assessments/<name>")
def assessment(name: str):
    data = load_assessment(name)
    return render_template("assessment.html", assessment=data, name=name)


@bp.post("/assessments/<name>/submit")
def assessment_submit(name: str):
    data = load_assessment(name)
    submitted = dict(request.form)

    score = 0
    results = []

    for q in data.get("questions", []):
        qid = q.get("id")
        picked = submitted.get(qid)
        correct = q.get("answer")
        ok = picked == correct
        score += 1 if ok else 0
        results.append(
            {
                "id": qid,
                "prompt": q.get("prompt"),
                "picked": picked,
                "correct": correct,
                "ok": ok,
            }
        )

    return render_template(
        "assessment_results.html",
        title=data.get("title", f"{name.title()} Assessment"),
        name=name,
        score=score,
        total=len(data.get("questions", [])),
        results=results,
    )
