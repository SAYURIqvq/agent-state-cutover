from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FieldType = Literal["str", "int", "float", "bool", "list", "dict", "null"]


@dataclass(frozen=True)
class FieldSpec:
    type: FieldType
    required: bool = False
    enum: tuple[Any, ...] | None = None

    def validate(self, path: str, value: Any) -> None:
        if not _matches_type(value, self.type):
            raise ValueError(f"{path} must be {self.type}, got {type(value).__name__}")
        if self.enum is not None and value not in self.enum:
            allowed = ", ".join(repr(item) for item in self.enum)
            raise ValueError(f"{path} must be one of: {allowed}")


class StateSchema:
    def __init__(self, fields: dict[str, FieldSpec]) -> None:
        self.fields = fields

    @classmethod
    def default(cls) -> "StateSchema":
        return cls(
            {
                "task.name": FieldSpec("str"),
                "task.current_step": FieldSpec("int"),
                "task.status": FieldSpec("str", enum=("new", "running", "blocked", "done")),
                "task.environment": FieldSpec("str", enum=("local", "staging", "production")),
                "task.database": FieldSpec("str"),
                "task.completed": FieldSpec("list"),
                "task.pending": FieldSpec("list"),
                "task.next": FieldSpec("str"),
                "infra.server_ip": FieldSpec("str"),
                "constraints": FieldSpec("list"),
                "notes.completed": FieldSpec("list"),
                "notes.pending": FieldSpec("list"),
                "notes.next": FieldSpec("list"),
                "notes.important": FieldSpec("list"),
            }
        )

    def assert_known(self, path: str) -> None:
        if path not in self.fields:
            raise ValueError(f"{path} is not declared in the state schema")

    def validate_value(self, path: str, value: Any) -> None:
        self.assert_known(path)
        self.fields[path].validate(path, value)

    def validate_state(self, state: dict[str, Any]) -> None:
        flat = flatten(state)
        for path, spec in self.fields.items():
            if spec.required and path not in flat:
                raise ValueError(f"{path} is required")
            if path in flat:
                spec.validate(path, flat[path])
        for path in flat:
            self.assert_known(path)


def flatten(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def get_path(state: dict[str, Any], path: str) -> Any:
    current: Any = state
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_path(state: dict[str, Any], path: str, value: Any) -> None:
    current = state
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
        if not isinstance(current, dict):
            raise ValueError(f"{path} crosses a non-object value at {part}")
    current[parts[-1]] = value


def unset_path(state: dict[str, Any], path: str) -> None:
    current = state
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.get(part)
        if not isinstance(current, dict):
            return
    current.pop(parts[-1], None)


def _matches_type(value: Any, expected: FieldType) -> bool:
    if expected == "str":
        return isinstance(value, str)
    if expected == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "bool":
        return isinstance(value, bool)
    if expected == "list":
        return isinstance(value, list)
    if expected == "dict":
        return isinstance(value, dict)
    if expected == "null":
        return value is None
    raise AssertionError(f"unknown type {expected}")
