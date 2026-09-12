from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint import CutoverEngine
from .patch import StatePatch


def main() -> None:
    parser = argparse.ArgumentParser(description="Hard context cutover reference CLI")
    parser.add_argument("--root", default=".agent_state", help="external memory directory")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create state and archive files")

    patch_parser = sub.add_parser("apply-patch", help="validate and commit a state patch")
    patch_parser.add_argument("--patch", required=True, help="path to a JSON state patch")
    patch_parser.add_argument("--source", default="llm", help="patch source label")

    projection_parser = sub.add_parser("checkpoint", help="create a hard-cutover prompt bundle")
    projection_parser.add_argument(
        "--projection",
        nargs="+",
        default=["task.current_step", "task.status", "task.next", "constraints"],
        help="state paths to include in the next window",
    )
    projection_parser.add_argument("--archive-tail", type=int, default=10)

    args = parser.parse_args()
    engine = CutoverEngine(Path(args.root))

    if args.command == "init":
        print(json.dumps(engine.init(), ensure_ascii=False, indent=2, sort_keys=True))
    elif args.command == "apply-patch":
        payload = json.loads(Path(args.patch).read_text(encoding="utf-8"))
        state = engine.apply_patch(StatePatch.from_dict(payload), source=args.source)
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.command == "checkpoint":
        checkpoint = engine.checkpoint(args.projection, args.archive_tail)
        print(checkpoint.to_prompt_bundle())


if __name__ == "__main__":
    main()
