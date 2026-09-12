from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .archive import Archive
from .patch import StatePatch
from .schema import StateSchema, get_path
from .store import JsonStateStore


@dataclass(frozen=True)
class Checkpoint:
    state_projection: dict[str, Any]
    notes: dict[str, Any]
    archive_tail: list[dict[str, Any]]
    created_at: str

    def to_prompt_bundle(self) -> str:
        payload = {
            "purpose": "Start a fresh context window from this checkpoint.",
            "state_projection": self.state_projection,
            "notes": self.notes,
            "recent_archive_events": self.archive_tail,
            "created_at": self.created_at,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


class CutoverEngine:
    def __init__(self, root: Path, schema: StateSchema | None = None) -> None:
        self.root = root
        self.schema = schema or StateSchema.default()
        self.store = JsonStateStore(root / "state.json")
        self.archive = Archive(root / "archive.jsonl")

    def init(self) -> dict[str, Any]:
        state = self.store.load()
        self.schema.validate_state(state)
        self.store.save(state)
        self.archive.append("system.init", {"state_path": str(self.store.path)})
        return state

    def apply_patch(self, patch: StatePatch, source: str = "llm") -> dict[str, Any]:
        before = self.store.load()
        after = patch.apply(before, self.schema)
        self.store.save(after)
        self.archive.append(
            "state.patch",
            {
                "source": source,
                "patch": {
                    "set": patch.set,
                    "unset": patch.unset,
                    "append": patch.append,
                },
            },
        )
        return after

    def checkpoint(self, projection_paths: list[str], archive_tail: int = 10) -> Checkpoint:
        state = self.store.load()
        projection = {path: get_path(state, path) for path in projection_paths}
        checkpoint = Checkpoint(
            state_projection=projection,
            notes=state.get("notes", {}),
            archive_tail=self.archive.tail(archive_tail),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "checkpoint.json").write_text(
            checkpoint.to_prompt_bundle() + "\n",
            encoding="utf-8",
        )
        return checkpoint
