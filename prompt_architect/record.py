"""Capture a real model run into a run file.

The evaluator is deliberately offline: it never calls a model. Something has to
produce the outputs once, and that is this module — a minimal, dependency-free
client for an OpenAI-compatible chat-completions endpoint.

The run file it writes is the same shape as the curated fixtures in
``benchmarks/runs/``, with one difference that matters: ``provenance.kind`` is
``"captured"``, and the endpoint, model id, and timestamp are recorded alongside
the outputs. A reader can therefore tell a measured run from an illustration
without trusting a filename.

Security note: the API key is read from the environment and never written to
disk, logged, or included in the run file.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import spec as spec_module

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_KEY_ENV = "OPENAI_API_KEY"


class RecordError(RuntimeError):
    """Raised when a run cannot be captured; never partially written."""


@dataclass
class RecordResult:
    path: Path
    cases: int
    model: str
    variant: str


def build_messages(spec_path: str | Path, variant: str, case_input: str) -> list[dict]:
    """System message = the composed prompt; user message = the case input.

    Keeping the case payload in the user turn is what the T1-T6 design assumes:
    the prompt is the contract, the ticket/document is data.
    """
    system = spec_module.render_file(spec_path, variant)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": case_input},
    ]


def call_chat(base_url: str, api_key: str, model: str, messages: list[dict],
              temperature: float = 0.0, max_tokens: int | None = None,
              timeout: float = 120.0) -> str:
    """POST to ``{base_url}/chat/completions`` and return the message content."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise RecordError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RecordError(f"cannot reach {url}: {exc.reason}") from exc

    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RecordError(f"unexpected response shape from {url}: {exc}") from exc

    if not isinstance(content, str):
        raise RecordError("response message content was not a string")
    return content


def record(spec_path: str | Path, suite_path: str | Path, variant: str, model: str,
           base_url: str = DEFAULT_BASE_URL, api_key: str | None = None,
           temperature: float = 0.0, max_tokens: int | None = None,
           out_path: str | Path | None = None, timeout: float = 120.0) -> RecordResult:
    """Render the prompt, call the endpoint once per suite case, write the run."""
    from . import evaluate  # local import keeps the module import-light

    suite = evaluate.load_suite(suite_path)
    spec_data = spec_module.load(spec_path)
    if not api_key:
        raise RecordError(
            "no API key provided; set the environment variable or pass --api-key-env"
        )
    if variant not in spec_module.VARIANTS:
        raise RecordError(f"unknown variant {variant!r}")

    outputs: dict[str, str] = {}
    for case in suite["cases"]:
        messages = build_messages(spec_path, variant, str(case.get("input", "")))
        outputs[case["id"]] = call_chat(
            base_url=base_url, api_key=api_key, model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        )

    run = {
        "suite": suite["name"],
        "prompt_version": str(suite.get("prompt_version", spec_data.version)),
        "variant": variant,
        "model": model,
        "temperature": temperature,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "provenance": {
            "kind": "captured",
            "endpoint_host": base_url.split("//", 1)[-1].split("/", 1)[0],
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "spec": f"{spec_data.name}@{spec_data.version}",
            "max_tokens": max_tokens,
            "note": "Captured by prompt_architect.record; grade with `prompt-architect eval`.",
        },
        "outputs": outputs,
    }

    if out_path is None:
        out_path = (Path("benchmarks") / "runs"
                    / f"{run['date']}.{suite['name']}.{variant}.json")
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return RecordResult(path=path, cases=len(outputs), model=model, variant=variant)


def key_from_env(name: str = DEFAULT_KEY_ENV) -> str | None:
    return os.environ.get(name) or None
