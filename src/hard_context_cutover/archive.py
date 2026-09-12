from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Archive:
    path: Path

    def append(self, kind: str, payload: dict[str, Any]) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event_id = str(uuid4())
        record = {
            "id": event_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return event_id

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
