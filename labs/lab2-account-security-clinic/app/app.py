from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import List

from flask import Flask, redirect, render_template, request, url_for


@dataclass(frozen=True)
class Module:
    key: str
    title: str
    summary: str
    minutes: str


MODULES: List[Module] = [
    Module(
        key="passwords",
        title="Passwords & Passphrases",
        summary="Build strong passphrases, compare common patterns, and discuss policy tradeoffs.",
        minutes="4–6 min",
    ),
    Module(
        key="mfa",
        title="MFA Push-Fatigue Simulator",
        summary="See why “Approve/Deny” prompts fail under pressure and how to teach safer defaults.",
        minutes="4–6 min",
    ),
    Module(
        key="recovery",
        title="Recovery & Account Resilience",
        summary="Recovery codes, backup options, and what to do when devices are lost or replaced.",
        minutes="3–5 min",
    ),
    Module(
        key="phishing_resistant",
        title="Phishing-Resistant Authentication",
        summary="WebAuthn/passkeys, security keys, and practical rollout guidance for schools.",
        minutes="3–5 min",
    ),
]


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            title="Lab 2 — Account Security Clinic",
            modules=MODULES,
        )

    @app.get("/module/<key>")
    def module(key: str):
        mod = next((m for m in MODULES if m.key == key), None)
        if not mod:
            return redirect(url_for("index"))

        if key == "passwords":
            return render_template("module_passwords.html", title=mod.title, module=mod)

        if key == "mfa":
            return render_template("module_mfa.html", title=mod.title, module=mod)

        if key == "recovery":
            codes = generate_recovery_codes(10)
            return render_template(
                "module_recovery.html",
                title=mod.title,
                module=mod,
                codes=codes,
            )

        if key == "phishing_resistant":
            return render_template(
                "module_phishing_resistant.html",
                title=mod.title,
                module=mod,
            )

        return redirect(url_for("index"))

    @app.post("/passwords/generate")
    def passwords_generate():
        length = _clamp_int(request.form.get("length", "18"), 10, 40)
        words = _clamp_int(request.form.get("words", "4"), 3, 7)
        separator = request.form.get("separator", "-")
        include_digit = request.form.get("include_digit") == "on"
        include_symbol = request.form.get("include_symbol") == "on"

        passphrase = generate_passphrase(words=words, separator=separator)

        if include_digit:
            passphrase += str(secrets.randbelow(10))
        if include_symbol:
            passphrase += secrets.choice("!@#$%")

        passphrase = _fit_to_length(passphrase, length)

        return render_template(
            "password_result.html",
            title="Passphrase Result",
            passphrase=passphrase,
            length=length,
            words=words,
            separator=separator,
            include_digit=include_digit,
            include_symbol=include_symbol,
        )

    return app


def _clamp_int(v: str, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except Exception:
        return lo
    return max(lo, min(hi, n))


def generate_passphrase(words: int, separator: str) -> str:
    wordlist = [
        "river", "planet", "canvas", "tomorrow", "orchard", "signal", "meadow", "harbor",
        "pencil", "window", "kernel", "pepper", "laptop", "mosaic", "forest", "cobalt",
        "paper", "castle", "violet", "ladder", "canyon", "honey", "thunder", "rocket",
        "ember", "garden", "prairie", "circle", "glacier", "bicycle", "comet", "silver",
    ]
    chosen = [secrets.choice(wordlist) for _ in range(words)]
    chosen = [w.capitalize() for w in chosen]
    return separator.join(chosen)


def _fit_to_length(s: str, target: int) -> str:
    if len(s) == target:
        return s
    if len(s) > target:
        return s[:target]
    pad = "".join(secrets.choice(string.ascii_lowercase) for _ in range(target - len(s)))
    return s + pad


def generate_recovery_codes(n: int) -> List[str]:
    codes = []
    for _ in range(n):
        part1 = secrets.randbelow(10**4)
        part2 = secrets.randbelow(10**4)
        codes.append(f"{part1:04d}-{part2:04d}")
    return codes


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
