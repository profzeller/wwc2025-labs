from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import docker
from docker.errors import NotFound


LABS_JSON_PATH = Path("/app/labs/labs.json")


@dataclass(frozen=True)
class LabPort:
    container_port: int
    host_port: int


@dataclass(frozen=True)
class LabSpec:
    id: str
    title: str
    description: str
    container_name: str
    image: str
    ports: list[LabPort]
    launch_url: str


def docker_client():
    return docker.from_env()


def load_labs() -> list[LabSpec]:
    with open(LABS_JSON_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    labs: list[LabSpec] = []
    for lab in raw.get("labs", []):
        ports = [
            LabPort(container_port=p["container_port"], host_port=p["host_port"])
            for p in lab.get("ports", [])
        ]

        labs.append(
            LabSpec(
                id=lab["id"],
                title=lab["title"],
                description=lab.get("description", ""),
                container_name=lab["container_name"],
                image=lab["image"],
                ports=ports,
                launch_url=lab["launch_url"],
            )
        )
    return labs


def get_running_lab_id() -> Optional[str]:
    client = docker_client()
    labs = load_labs()
    for lab in labs:
        try:
            c = client.containers.get(lab.container_name)
            c.reload()
            if c.status == "running":
                return lab.id
        except NotFound:
            continue
    return None


def _stop_container_if_running(container_name: str, timeout: int = 5) -> bool:
    """
    Returns True if a running container was stopped, else False.
    """
    client = docker_client()
    try:
        c = client.containers.get(container_name)
        c.reload()
        if c.status == "running":
            c.stop(timeout=timeout)
            return True
    except NotFound:
        return False
    return False


def stop_all_labs(labs: list[LabSpec]) -> None:
    for lab in labs:
        _stop_container_if_running(lab.container_name)


def _ensure_image_exists(image: str) -> None:
    """
    Hub does NOT build images. Images must be built via docker compose.
    """
    client = docker_client()
    client.images.get(image)


def _remove_existing_container_if_present(container_name: str) -> None:
    client = docker_client()
    try:
        existing = client.containers.get(container_name)
        existing.reload()
        if existing.status != "running":
            existing.remove(force=True)
    except NotFound:
        return


def _start_container(lab: LabSpec) -> None:
    client = docker_client()
    port_map = {f"{p.container_port}/tcp": p.host_port for p in lab.ports}

    client.containers.run(
        lab.image,
        name=lab.container_name,
        detach=True,
        ports=port_map,
        restart_policy={"Name": "no"},
    )


def _wait_for_ready(container_name: str, seconds: float = 30.0) -> str:
    """
    Wait until:
      1) container status is 'running', AND
      2) if a Docker HEALTHCHECK exists, it becomes 'healthy'

    Returns a string describing readiness mode:
      - "healthy" if healthcheck reported healthy
      - "running" if no healthcheck is present (or Docker doesn't report one)

    This avoids "launching too early" without making host-network assumptions.
    """
    client = docker_client()
    deadline = time.time() + seconds

    last_status = None
    last_health = None
    saw_health = False

    while time.time() < deadline:
        try:
            c = client.containers.get(container_name)
            c.reload()

            last_status = c.status

            # Inspect health info if present
            state = (c.attrs or {}).get("State", {}) or {}
            health = state.get("Health")
            if health is not None:
                saw_health = True
                last_health = health.get("Status")

            if c.status != "running":
                time.sleep(0.25)
                continue

            if saw_health:
                if last_health == "healthy":
                    return "healthy"
                # still starting/unhealthy
                time.sleep(0.35)
                continue

            # No healthcheck present; give a brief grace window
            time.sleep(0.35)
            return "running"

        except NotFound:
            last_status = "not-found"
            time.sleep(0.25)

    if saw_health:
        raise RuntimeError(
            f"Container did not become healthy in time (status={last_status}, health={last_health})."
        )

    raise RuntimeError(f"Container did not reach 'running' state in time (last status: {last_status}).")


def start_lab(lab_id: str) -> LabSpec:
    labs = load_labs()
    lab = next((l for l in labs if l.id == lab_id), None)
    if not lab:
        raise ValueError(f"Unknown lab_id: {lab_id}")

    stop_all_labs(labs)

    try:
        _ensure_image_exists(lab.image)
    except Exception:
        raise ValueError(
            f"Lab image not found locally: {lab.image}. "
            f"Build it with: docker compose build {lab.id}  (or: docker compose --profile labs build)"
        )

    _remove_existing_container_if_present(lab.container_name)
    _start_container(lab)

    _wait_for_ready(lab.container_name)

    return lab


def start_lab_steps(lab_id: str) -> Iterator[dict]:
    """
    Yields dict events suitable for SSE streaming to the UI.
    """
    labs = load_labs()
    lab = next((l for l in labs if l.id == lab_id), None)
    if not lab:
        yield {"type": "error", "message": f"Unknown lab_id: {lab_id}"}
        return

    yield {"type": "step", "message": "Stopping any other running labs..."}
    for other in labs:
        if other.id == lab.id:
            continue
        stopped = _stop_container_if_running(other.container_name)
        if stopped:
            yield {"type": "step", "message": f"Stopped {other.title}."}

    yield {"type": "step", "message": f"Ensuring image exists: {lab.image} ..."}
    try:
        _ensure_image_exists(lab.image)
        yield {"type": "step", "message": "Image found locally."}
    except Exception:
        yield {
            "type": "error",
            "message": (
                f"Image not found: {lab.image}. "
                f"Build lab images with: docker compose build {lab.id}  (or: docker compose --profile labs build)"
            ),
        }
        return

    yield {"type": "step", "message": "Cleaning up any previous stopped container..."}
    _remove_existing_container_if_present(lab.container_name)

    yield {"type": "step", "message": f"Starting container: {lab.container_name} ..."}
    try:
        _start_container(lab)
    except Exception as e:
        yield {"type": "error", "message": f"Failed to start container: {e}"}
        return

    yield {"type": "step", "message": "Waiting for container readiness (running/healthy)..."}
    try:
        mode = _wait_for_ready(lab.container_name)
    except Exception as e:
        yield {"type": "error", "message": str(e)}
        return

    if mode == "healthy":
        yield {"type": "step", "message": "Healthcheck is healthy."}
    else:
        yield {"type": "step", "message": "Container is running (no healthcheck detected)."}

    yield {"type": "done", "message": "Lab is ready.", "launch_url": lab.launch_url}


def stop_all_labs_steps() -> Iterator[dict]:
    labs = load_labs()
    yield {"type": "step", "message": "Stopping all labs..."}

    any_stopped = False
    for lab in labs:
        stopped = _stop_container_if_running(lab.container_name)
        if stopped:
            any_stopped = True
            yield {"type": "step", "message": f"Stopped {lab.title}."}

    if not any_stopped:
        yield {"type": "step", "message": "No running lab containers were found."}

    yield {"type": "done", "message": "All labs stopped."}
