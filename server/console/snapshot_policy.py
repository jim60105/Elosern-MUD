"""Process-local, fail-fast save policy shared by all console writes."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable

from server.console import execution
from server.console.errors import ConsoleError
from server.saves import snapshot
from server.saves.layout import SaveInProgress
from world.observability import log_error, log_info
from world.rules.clock import read_world_clock


@dataclass
class Attempt:
    needs_save: bool = False
    result: dict[str, Any] | None = None
    error: Exception | None = None
    advance: int = 0


class SnapshotPolicy:
    """Injectable coordinator; live process uses the singleton below."""

    def __init__(self, *, runner=None, clock_reader=None, saver=None):
        self.baseline_tick: int | None = None
        self._lock = threading.Lock()
        self.runner = runner or execution.run_on_gameplay_thread
        self.clock_reader = clock_reader or read_world_clock
        self.saver = saver

    def _tick(self) -> int | None:
        clock = self.clock_reader()
        return None if clock is None else int(clock.tick)

    def status(self) -> dict[str, Any]:
        tick = self._tick()
        return {
            "tick": tick,
            "baseline_tick": self.baseline_tick,
            "will_snapshot": self.baseline_tick is None or tick != self.baseline_tick,
            "snapshot": {"taken": False, "save_id": None},
        }

    @staticmethod
    def _represented_tick(info) -> int | None:
        clock = info.clock
        tick = clock.get("tick") if isinstance(clock, dict) else None
        return tick if type(tick) is int and tick >= 0 else None

    def _save(self, kind, label, **kwargs):
        return (self.saver or snapshot.create_snapshot)(kind, label, **kwargs)

    def manual_save(self, label: str, **kwargs):
        """Keep S5's existing refusal and baseline unchanged on any failure."""
        if execution.in_handoff() or not self._lock.acquire(blocking=False):
            raise SaveInProgress("a console operation or save is already running")
        try:
            info = self._save("manual", label, **kwargs)
            self.baseline_tick = self._represented_tick(info)
            return info
        finally:
            self._lock.release()

    def execute(self, operation: Callable[[], dict[str, Any]], *, action: str,
                account: str, target: str, arguments: str = "") -> dict[str, Any]:
        saved = {"taken": False, "save_id": None}
        error = None
        result = None
        acquired = False
        try:
            if execution.in_handoff() or not self._lock.acquire(blocking=False):
                raise ConsoleError("snapshot_failed", "console_in_progress")
            acquired = True

            def attempt(check_policy: bool) -> Attempt:
                start = self._tick()
                if start is None:
                    raise ConsoleError("target_not_found", "world_clock")
                if check_policy and (self.baseline_tick is None or start != self.baseline_tick):
                    return Attempt(needs_save=True)
                try:
                    outcome = operation()
                except Exception as failure:  # observability: ignore R2: settled outcome is logged once by the shared boundary below
                    return Attempt(error=failure, advance=(self._tick() or 0) - start)
                return Attempt(result=outcome, advance=(self._tick() or 0) - start)

            outcome = self.runner(lambda: execution.guarded(lambda: attempt(True)))
            if outcome.needs_save:
                try:
                    info = self._save("auto_intervention", f"GM {action}")
                except Exception as failure:
                    reason = "save_in_progress" if isinstance(failure, SaveInProgress) else "save_failed"
                    raise ConsoleError("snapshot_failed", reason) from failure
                saved = {"taken": True, "save_id": info.id}
                represented = self._represented_tick(info)
                outcome = self.runner(lambda: execution.guarded(lambda: attempt(False)))
            else:
                represented = self.baseline_tick
            self.baseline_tick = None if represented is None else represented + outcome.advance
            if outcome.error is not None:
                raise outcome.error
            result = {**outcome.result, "snapshot": saved}
        except Exception as failure:  # observability: ignore R2: the single final boundary event below carries this exception
            error = failure
        finally:
            if acquired:
                self._lock.release()
        context = {
            "account": account, "action": action, "target": target,
            "arguments": arguments[:200],
            "outcome": "committed" if error is None else getattr(error, "code", "internal_error"),
            "save": saved["save_id"],
        }
        if error is None:
            log_info("gm_action", context=context)
            return result
        if isinstance(error, ConsoleError):
            error.snapshot = saved
            log_info("gm_action", context=context)
            raise error
        log_error("gm_action", context=context, exc=error)
        refusal = ConsoleError("internal_error")
        refusal.snapshot = saved
        raise refusal from error


policy = SnapshotPolicy()


def status():
    return policy.status()


def manual_save(label: str, **kwargs):
    return policy.manual_save(label, **kwargs)
