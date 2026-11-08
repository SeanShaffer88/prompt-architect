"""Minimal, dependency-free YAML front-matter reader.

Supports the subset this repository actually uses:

    ---
    name: code-generation
    type: blueprint
    version: 1.0.0
    inputs: [language, platform]
    output_format: markdown-code-fence
    related:
      - chain-of-thought
      - constraint-enforcement
    ---

Scalars, inline lists, block lists, quoted strings, and trailing ``#`` comments.
Anything richer is a spec bug, not a parsing problem — fail loudly instead of
silently guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    """A Markdown file split into front-matter metadata and body text."""

    path: Path
    meta: dict = field(default_factory=dict)
    body: str = ""
    raw: str = ""

    @property
    def has_front_matter(self) -> bool:
        return bool(self.meta)


def _strip_comment(value: str) -> str:
    """Remove a trailing ``# comment`` from an unquoted scalar."""
    if value[:1] in {'"', "'"}:
        return value
    depth = 0
    for i, ch in enumerate(value):
        if ch in "[(":
            depth += 1
        elif ch in "])":
            depth -= 1
        elif ch == "#" and depth == 0 and i > 0 and value[i - 1] == " ":
            return value[:i].rstrip()
    return value


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _coerce(value: str):
    value = _strip_comment(value).strip()
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_unquote(part) for part in inner.split(",") if part.strip()]
    if value in {"true", "false"}:
        return value == "true"
    return _unquote(value)


def parse_meta(text: str) -> dict:
    """Parse the front-matter block into a flat dict."""
    meta: dict = {}
    current_key: str | None = None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        if stripped.startswith("- ") and current_key is not None:
            existing = meta.get(current_key)
            if not isinstance(existing, list):
                existing = []
            existing.append(_unquote(stripped[2:]))
            meta[current_key] = existing
            continue
        if ":" not in line:
            raise ValueError(f"front-matter line is not key: value -> {line!r}")
        key, _, value = line.partition(":")
        current_key = key.strip()
        meta[current_key] = _coerce(value)
    return meta


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return ``(meta, body)``. Files without front-matter yield ``({}, text)``."""
    # Normalise BOM and CRLF so headings and delimiters match reliably.
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    for i in range(1, len(lines)):
        if lines[i].strip() in {"---", "..."}:
            meta_text = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1:])
            return parse_meta(meta_text), body
    return {}, text


def load(path: str | Path) -> Document:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    meta, body = split_front_matter(raw)
    return Document(path=path, meta=meta, body=body, raw=raw)
