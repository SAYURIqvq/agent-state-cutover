from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INITIAL_STATE: dict[str, Any] = {
    "task": {
        "name": "",
        "current_step": 0,
        "status": "new",
        "environment": "staging",
        "database": "",
        "completed": [],
        "pending": [],
        "next": "",
    },
    "infra": {"server_ip": ""},
    "constraints": ["禁止修改 production"],
    "notes": {
        "completed": [],
        "pending": [],
        "next": [],
        "important": [],
    },
}


@dataclass(frozen=True)
class JsonStateStore:
    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(INITIAL_STATE, ensure_ascii=False))
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
