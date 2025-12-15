from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort

from .docker_control import (
    load_labs,
    start_lab,
    stop_all_labs,
    get_running_lab_id,
)

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


@bp.post("/labs/start/<lab_id>")
def labs_start(lab_id: str):
    try:
        lab = start_lab(lab_id)
        flash(f"Started {lab.title}. Launch: {lab.launch_url}", "success")
    except Exception as e:
        flash(f"Failed to start lab '{lab_id}': {e}", "error")
    return redirect(url_for("hub.index"))


@bp.get("/labs/start-and-launch/<lab_id>")
def labs_start_and_launch(lab_id: str):
    """
    Stop any running labs, start the selected lab, then redirect to its launch URL.
    """
    try:
        lab = start_lab(lab_id)
        return redirect(lab.launch_url)
    except Exception as e:
        flash(f"Failed to start lab '{lab_id}': {e}", "error")
        return redirect(url_for("hub.index"))


@bp.post("/labs/stop")
def labs_stop():
    labs = load_labs()
    stop_all_labs(labs)
    flash("Stopped all labs.", "success")
    return redirect(url_for("hub.index"))


@bp.get("/assessments")
def assessments_index():
    """
    Simple index page for available assessments.
    """
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
