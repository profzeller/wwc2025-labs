from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify

from .docker_control import (
    load_labs,
    start_lab,
    stop_all_labs,
    get_running_lab_id,
)

bp = Blueprint("hub", __name__)

ASSESSMENTS_DIR = (Path(__file__).resolve().parent / "assessments").resolve()

# In-memory job status for async actions
# START_JOBS["lab1"] -> {"state":"starting|running|error", "message":"...", "started_at":...}
# STOP_JOB -> {"state":"stopping|stopped|error", "message":"...", "started_at":...}
START_JOBS: dict[str, dict[str, Any]] = {}
STOP_JOB: dict[str, Any] | None = None

LOCK = threading.Lock()


def load_assessment(name: str) -> dict:
    path = (ASSESSMENTS_DIR / f"{name}.json").resolve()
    if not str(path).startswith(str(ASSESSMENTS_DIR)):
        abort(404)
    if not path.exists() or not path.is_file():
        abort(404)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _set_start_job(lab_id: str, state: str, message: str = "") -> None:
    with LOCK:
        START_JOBS[lab_id] = {"state": state, "message": message, "started_at": time.time()}


def _get_start_job(lab_id: str) -> dict[str, Any] | None:
    with LOCK:
        return START_JOBS.get(lab_id)


def _set_stop_job(state: str, message: str = "") -> None:
    global STOP_JOB
    with LOCK:
        STOP_JOB = {"state": state, "message": message, "started_at": time.time()}


def _get_stop_job() -> dict[str, Any] | None:
    with LOCK:
        return STOP_JOB


def _start_lab_worker(lab_id: str) -> None:
    def step(msg: str) -> None:
        _set_start_job(lab_id, "starting", msg)

    try:
        step("Queued…")
        lab = start_lab(lab_id, step=step)
        _set_start_job(lab_id, "running", f"Running. Launch: {lab.launch_url}")
    except Exception as e:
        _set_start_job(lab_id, "error", str(e))


def _stop_all_worker() -> None:
    try:
        _set_stop_job("stopping", "Stopping any running labs…")
        labs = load_labs()

        def step(msg: str) -> None:
            _set_stop_job("stopping", msg)

        stop_all_labs(labs, step=step)
        _set_stop_job("stopped", "All labs stopped.")
    except Exception as e:
        _set_stop_job("error", str(e))


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


# -------------------------
# Async API (UI modal)
# -------------------------

@bp.post("/api/labs/start/<lab_id>")
def api_labs_start(lab_id: str):
    existing = _get_start_job(lab_id)
    if existing and existing.get("state") == "starting":
        return jsonify({"ok": True, "state": "starting"})

    _set_start_job(lab_id, "starting", "Queued…")

    t = threading.Thread(target=_start_lab_worker, args=(lab_id,), daemon=True)
    t.start()

    return jsonify({"ok": True, "state": "starting"})


@bp.post("/api/labs/stop")
def api_labs_stop():
    existing = _get_stop_job()
    if existing and existing.get("state") == "stopping":
        return jsonify({"ok": True, "state": "stopping"})

    _set_stop_job("stopping", "Queued…")

    t = threading.Thread(target=_stop_all_worker, daemon=True)
    t.start()

    return jsonify({"ok": True, "state": "stopping"})


@bp.get("/api/labs/status")
def api_labs_status():
    running = get_running_lab_id()
    labs = load_labs()

    with LOCK:
        jobs = dict(START_JOBS)
        stop_job = dict(STOP_JOB) if STOP_JOB else None

    launch_map = {l.id: l.launch_url for l in labs}

    return jsonify(
        {
            "ok": True,
            "running_lab_id": running,
            "jobs": jobs,
            "stop_job": stop_job,
            "launch_map": launch_map,
        }
    )


# -------------------------
# Assessments
# -------------------------

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
            {"id": qid, "prompt": q.get("prompt"), "picked": picked, "correct": correct, "ok": ok}
        )

    return render_template(
        "assessment_results.html",
        title=data.get("title", f"{name.title()} Assessment"),
        name=name,
        score=score,
        total=len(data.get("questions", [])),
        results=results,
    )
