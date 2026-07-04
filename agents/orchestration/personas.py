"""Persona/prompt loader -- one system persona per agent.

Owner: aminssutt. Ticket: AGA.4 (#31).

Each agent's system prompt lives as a markdown file in ``personas/<name>.md``
so it is reviewable in isolation (acceptance criterion: prompts reviewed by
vgtray) and versioned separately from code. LLM-backed agents load their
persona and build ``messages=[{"role": "system", "content": load_persona(...)},
{"role": "user", "content": ...}]`` for ``VultrClient.chat`` / ``structured_json``.
"""

from __future__ import annotations

import pathlib

_PERSONA_DIR = pathlib.Path(__file__).parent / "personas"


def persona_path(name: str) -> pathlib.Path:
    return _PERSONA_DIR / f"{name}.md"


def load_persona(name: str) -> str:
    """Return the system persona text for ``name`` (raises if absent)."""
    path = persona_path(name)
    if not path.is_file():
        raise FileNotFoundError(
            f"no persona for agent {name!r} at {path}; "
            f"available: {available_personas()}"
        )
    return path.read_text(encoding="utf-8")


def available_personas() -> list[str]:
    """Sorted agent names that have a persona file."""
    if not _PERSONA_DIR.is_dir():
        return []
    return sorted(p.stem for p in _PERSONA_DIR.glob("*.md"))
