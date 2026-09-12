import pytest

from hard_context_cutover.patch import PatchValidationError, StatePatch
from hard_context_cutover.schema import StateSchema
from hard_context_cutover.store import INITIAL_STATE


def test_patch_applies_minimal_mutation():
    patch = StatePatch.from_dict(
        {
            "set": {"task.current_step": 73, "task.status": "running"},
            "append": {"task.completed": ["创建数据库"]},
        }
    )

    state = patch.apply(INITIAL_STATE, StateSchema.default())

    assert state["task"]["current_step"] == 73
    assert state["task"]["status"] == "running"
    assert state["task"]["completed"] == ["创建数据库"]
    assert state["constraints"] == ["禁止修改 production"]


def test_patch_rejects_unknown_field():
    patch = StatePatch.from_dict({"set": {"made_up.field": "oops"}})

    with pytest.raises(ValueError, match="not declared"):
        patch.apply(INITIAL_STATE, StateSchema.default())


def test_patch_rejects_wrong_type():
    patch = StatePatch.from_dict({"set": {"task.current_step": "不知道"}})

    with pytest.raises(ValueError, match="must be int"):
        patch.apply(INITIAL_STATE, StateSchema.default())


def test_patch_rejects_overlapping_ops():
    patch = StatePatch.from_dict(
        {
            "set": {"task.next": "配置 Nginx"},
            "unset": ["task.next"],
        }
    )

    with pytest.raises(PatchValidationError, match="only one operation"):
        patch.apply(INITIAL_STATE, StateSchema.default())
