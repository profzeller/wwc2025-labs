from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import docker
from docker.errors import NotFound

LABS_JSON_PATH = Path("/labs/labs.json")


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


def stop_all_labs(labs: list[LabSpec], step: Optional[Callable[[str], None]] = None) -> None:
    client = docker_client()
    for lab in labs:
        try:
            c = client.containers.get(lab.container_name)
            if c.status == "running":
                if step:
                    step(f"Stopping {lab.container_name}…")
                c.stop(timeout=10)
        except NotFound:
            pass


def get_running_lab_id() -> Optional[str]:
    client = docker_client()
    labs = load_labs()
    for lab in labs:
        try:
            c = client.containers.get(lab.container_name)
            if c.status == "running":
                return lab.id
        except NotFound:
            continue
    return None


def start_lab(lab_id: str, step: Optional[Callable[[str], None]] = None) -> LabSpec:
    labs = load_labs()
    lab = next((l for l in labs if l.id == lab_id), None)
    if not lab:
        raise ValueError(f"Unknown lab_id: {lab_id}")

    client = docker_client()

    if step:
        step("Stopping any running labs…")
    stop_all_labs(labs, step=step)

    if step:
        step("Ensuring lab image is available…")
    try:
        client.images.get(lab.image)
    except Exception:
        raise ValueError(
            f"Lab image not found locally: {lab.image}. "
            f"Run: docker compose build (or docker compose --profile labs up -d --build)"
        )

    # Clean restart if container exists but isn't running
    if step:
        step("Preparing container…")
    try:
        existing = client.containers.get(lab.container_name)
        if existing.status == "running":
            # should not happen because we stop first, but keep safe
            if step:
                step("Stopping existing container…")
            existing.stop(timeout=10)
        if step:
            step("Removing old container…")
        existing.remove(force=True)
    except NotFound:
        pass

    if step:
        step("Starting container…")
    port_map = {f"{p.container_port}/tcp": p.host_port for p in lab.ports}

    client.containers.run(
        lab.image,
        name=lab.container_name,
        detach=True,
        ports=port_map,
        restart_policy={"Name": "no"},
    )

    if step:
        step("Container started. Waiting for readiness…")

    return lab
