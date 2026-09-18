"""Shared immutable-container rejection for frozen proposal dataclasses.

``reject_mutable_containers`` is the single copy of the recursive
``dict``/``list``-under-``value`` refusal used by the proposal dataclasses
in ``world/ai/action_options.py`` and ``world/ai/scenario_director.py``, so
a fix or tightening of the immutability gate applies to every layer at
once. Imports only the dataclasses reflection helpers and ``typing`` —
no Evennia, jsonschema, or transport surface — preserving the
import-boundary contracts of its consumers.
"""

from dataclasses import fields, is_dataclass
from typing import Any


def reject_mutable_containers(value: Any, path: str) -> None:
    """Reject any ``dict``/``list`` nested under ``value`` so immutability is
    enforced by construction, not only by the frozen dataclass."""
    if isinstance(value, (dict, list)):
        raise TypeError(f"{path} holds a mutable dict/list container")
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            reject_mutable_containers(item, f"{path}[{index}]")
    elif is_dataclass(value):
        for dataclass_field in fields(value):
            reject_mutable_containers(
                getattr(value, dataclass_field.name),
                f"{path}.{dataclass_field.name}",
            )