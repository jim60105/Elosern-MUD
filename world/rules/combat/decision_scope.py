"""Ephemeral execution identity for the decision one action slot resolves.

The round engine knows something a decision provider cannot: which real round
it is resolving and which of an actor's action slots it is provisioning. A
provider keeps its two-argument shape, and that identity travels beside it in a
context variable instead of through its arguments.

Two layers, deliberately: the orchestration owner supplies an
:class:`ExecutionScopeBase` (the session, the actual round number and the
resolved context mode) and the round engine adds the acting combatant's stable
identity plus the slot index it is provisioning. Nothing here is durable, and
nothing here is read by settlement: the scope exists so a decision can be
reproduced against the identity it was actually made under.

``stable_actor_id`` restates the snapshot's stable-identity convention
(``dbref:`` then ``key:``; :func:`world.rules.monster_ai.models.stable_identity`)
rather than importing it, so the combat core stays free of the monster-AI
package; ``world.rules.tests.test_monster_ai_selection`` pins the two
expressions together.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class ExecutionScopeBase:
    """The encounter-level identity one round's decisions are numbered from.

    ``session_id`` is empty for an orchestration without a persistent session
    (a bounded ``run_battle`` encounter or a direct overwhelm call), and
    ``context_mode`` names the resolved context the round runs under
    (``"normal"`` or ``"overwhelm"``).
    """

    session_id: str = ""
    round_index: int = 0
    context_mode: str = "normal"

    def at_round(self, index: int, *, context_mode: str | None = None) -> "ExecutionScopeBase":
        """Return this base respecified for one actual round index."""
        return replace(
            self,
            round_index=index,
            context_mode=self.context_mode if context_mode is None else context_mode,
        )


@dataclass(frozen=True, slots=True)
class ExecutionScope:
    """One action slot's real identity while its provider is called."""

    session_id: str
    round_index: int
    actor_id: str
    slot_index: int
    context_mode: str = "normal"


def stable_actor_id(entity: Any) -> str:
    """Return one combatant's stable identity: its dbref, else its object key."""
    dbref = getattr(entity, "pk", None)
    if dbref is None:
        return f"key:{getattr(entity, 'key', '')}"
    return f"dbref:{dbref}"


_CURRENT_SCOPE: ContextVar[ExecutionScope | None] = ContextVar(
    "decision_execution_scope", default=None
)


@contextmanager
def decision_scope(scope: ExecutionScope) -> Iterator[ExecutionScope]:
    """Install one action slot's scope for the duration of its provider call.

    The previous scope (the enclosing round's, or ``None`` outside any) is
    restored on normal return and on every exception the provider raises.
    """
    token = _CURRENT_SCOPE.set(scope)
    try:
        yield scope
    finally:
        _CURRENT_SCOPE.reset(token)


def current_decision_scope() -> ExecutionScope | None:
    """Return the action slot's scope, or ``None`` outside an execution."""
    return _CURRENT_SCOPE.get()


def decision_scope_for(
    base: ExecutionScopeBase | None,
    *,
    actor_id: str,
    slot_index: int,
) -> ExecutionScope:
    """Return one provider call's scope from its encounter base and slot."""
    resolved = ExecutionScopeBase() if base is None else base
    return ExecutionScope(
        session_id=resolved.session_id,
        round_index=resolved.round_index,
        actor_id=actor_id,
        slot_index=slot_index,
        context_mode=resolved.context_mode,
    )
