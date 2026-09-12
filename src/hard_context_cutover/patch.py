from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from .schema import StateSchema, get_path, set_path, unset_path


class PatchValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StatePatch:
    set: dict[str, Any] = field(default_factory=dict)
    unset: list[str] = field(default_factory=list)
    append: dict[str, list[Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StatePatch":
        allowed = {"set", "unset", "append"}
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise PatchValidationError(f"unknown patch operations: {', '.join(unknown)}")
        patch = cls(
            set=dict(payload.get("set", {})),
            unset=list(payload.get("unset", [])),
            append=dict(payload.get("append", {})),
        )
        patch._validate_shape()
        return patch

    def apply(self, state: dict[str, Any], schema: StateSchema) -> dict[str, Any]:
        self.validate(schema)
        next_state = deepcopy(state)

        for path, value in self.set.items():
            set_path(next_state, path, value)

        for path, values in self.append.items():
            current = get_path(next_state, path)
            if current is None:
                current = []
                set_path(next_state, path, current)
            if not isinstance(current, list):
                raise PatchValidationError(f"{path} must be a list before append")
            current.extend(values)

        for path in self.unset:
            unset_path(next_state, path)

        schema.validate_state(next_state)
        return next_state

    def validate(self, schema: StateSchema) -> None:
        touched = set(self.set) | set(self.unset) | set(self.append)
        if not touched:
            raise PatchValidationError("patch must touch at least one state field")
        if len(touched) != len(self.set) + len(self.unset) + len(self.append):
            raise PatchValidationError("a field can appear in only one operation")

        for path, value in self.set.items():
            schema.validate_value(path, value)
        for path in self.unset:
            schema.assert_known(path)
        for path, values in self.append.items():
            schema.validate_value(path, [])
            if not isinstance(values, list):
                raise PatchValidationError(f"append.{path} must be a list of values")

    def _validate_shape(self) -> None:
        if not isinstance(self.set, dict):
            raise PatchValidationError("set must be an object")
        if not isinstance(self.unset, list) or not all(isinstance(item, str) for item in self.unset):
            raise PatchValidationError("unset must be a list of field paths")
        if not isinstance(self.append, dict):
            raise PatchValidationError("append must be an object")
