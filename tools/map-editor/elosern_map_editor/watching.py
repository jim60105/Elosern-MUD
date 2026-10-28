"""Continuous workspace file following: the one watch coordinator.

The service watches the source, layout and artifact roots for creation,
replacement, renaming and deletion (including documents and directories that
appear later), coalesces the notifications until the directories settle, and
then reconciles one complete fresh read (:meth:`EditorService.follow`). A
notification is never trusted or suppressed by itself: the read is compared
with the committed fingerprint ledger, so the service's own delayed or
coalesced notifications keep the history and any other loaded content is an
adopted external change. A debounce is not a multi-file transaction.

Watched roots (:func:`watch_plan`):

- ``content/`` recursively: world sources, editor layouts and the reference
  context artifact;
- the partition artifact's directory, non-recursively, filtered to the file;
- the external context source closure where available: the literal
  directory prefix of each glob discovery rule of the current reference
  context recursively, and each literal rule file through its parent
  directory, non-recursively and filtered to the file;
- a root that does not exist yet is replaced by its nearest existing
  ancestor (non-recursive, filtered to the path towards the root), and the
  plan is recomputed after every reconciliation, so a created root starts to
  be watched (with a reconciliation right after the restart).

Every (re)start reconciles once as soon as the watcher reports that it is
established, which closes the gap between the previous read and the watch.
A watcher failure is reported in ``following`` and retried with a backoff.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import watchfiles

from .confinement import PARTITION_ARTIFACT, REFERENCE_CONTEXT_ARTIFACT, ConfinementError, split_relative

#: Recursively watched authored roots (sources, layouts, reference context).
AUTHORED_ROOTS = ("content",)
#: Seconds the Rust watcher waits before reporting an idle timeout.
IDLE_TIMEOUT_MS = 500
#: Upper bound of the coalescing window, in milliseconds.
DEBOUNCE_MS = 1600
_GLOB = frozenset("*?[")


@dataclass(frozen=True, slots=True)
class WatchPlan:
    """Absolute paths: recursive directories, flat directories, flat targets."""

    recursive: tuple[str, ...]
    flat: tuple[str, ...]
    targets: tuple[str, ...]


def _literal(rule: str) -> tuple[tuple[str, ...], bool]:
    """The literal leading components of a rule and whether it is a file."""

    parts = split_relative(rule)
    literal: list[str] = []
    for part in parts:
        if _GLOB & set(part):
            return tuple(literal), False
        literal.append(part)
    return tuple(literal), True


def _real_directory(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def discovery_rules(root: Path, limit: int = 8 * 1024 * 1024) -> tuple[str, ...]:
    """The current reference context's discovery rules, or none if unreadable."""

    path = root / REFERENCE_CONTEXT_ARTIFACT
    try:
        if path.is_symlink() or path.stat().st_size > limit:
            return ()
        rules = json.loads(path.read_text(encoding="utf-8")).get("discovery_rules", ())
    except (OSError, ValueError, AttributeError):
        return ()
    return tuple(rule for rule in rules if isinstance(rule, str)) if isinstance(rules, list) else ()


def watch_plan(root: str | os.PathLike[str], rules: tuple[str, ...] = ()) -> WatchPlan:
    """Which directories to watch for ``root`` and these discovery rules."""

    root = Path(root)
    directories: set[tuple[str, ...]] = {tuple(item.split("/")) for item in AUTHORED_ROOTS}
    files: set[tuple[str, ...]] = {tuple(PARTITION_ARTIFACT.split("/"))}
    for rule in rules:
        try:
            parts, is_file = _literal(rule)
        except ConfinementError:
            continue  # an unsafe rule is never watched (nor globbed)
        if not parts:
            continue  # a rule globbing the root itself is not watchable here
        (files if is_file else directories).add(parts)

    recursive: set[Path] = set()
    flat: set[Path] = set()
    targets: set[Path] = set()

    def nearest(parts: tuple[str, ...]) -> Path:
        current = root
        for part in parts:
            candidate = current / part
            if not _real_directory(candidate):
                break
            current = candidate
        return current

    for parts in directories:
        path = root.joinpath(*parts)
        if _real_directory(path):
            recursive.add(path)
        else:
            flat.add(nearest(parts))
            targets.add(path)
    for parts in files:
        path = root.joinpath(*parts)
        flat.add(nearest(parts[:-1]))
        targets.add(path)

    def covered(path: Path) -> bool:
        return any(path == base or base in path.parents for base in recursive)

    # Nested recursive roots and flat watches inside them are redundant.
    recursive = {path for path in recursive if not any(base in path.parents for base in recursive)}
    flat = {path for path in flat if not covered(path)}
    targets = {path for path in targets if not covered(path)}
    return WatchPlan(
        recursive=tuple(sorted(map(str, recursive))),
        flat=tuple(sorted(map(str, flat))),
        targets=tuple(sorted(map(str, targets))),
    )


def flat_filter(targets: tuple[str, ...]) -> Callable[[watchfiles.Change, str], bool]:
    """Accept a flat-directory change only on (or towards) a watched target."""

    def accept(change: watchfiles.Change, path: str) -> bool:
        return any(target == path or target.startswith(path + os.sep) for target in targets)

    return accept


class WatchCoordinator:
    """Runs the watch loops for one service and reconciles each batch."""

    def __init__(
        self,
        service,
        *,
        awatch: Callable[..., Any] | None = None,
        retry_seconds: float = 2.0,
        max_retry_seconds: float = 30.0,
    ) -> None:
        self.service = service
        self.root = Path(service.config.workspace_root)
        self._awatch = awatch or watchfiles.awatch
        self._retry = retry_seconds
        self._max_retry = max_retry_seconds
        self._task: asyncio.Task | None = None

    def plan(self) -> WatchPlan:
        return watch_plan(self.root, discovery_rules(self.root, self.service.config.limits.max_artifact_bytes))

    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self.service.following["active"] = False

    def _status(self, **values) -> None:
        with self.service._state:
            self.service.following.update(values)

    async def _run(self) -> None:
        delay = self._retry
        while True:
            try:
                await self._watch(await asyncio.to_thread(self.plan))
                delay = self._retry  # a plan change: restart at once
            except asyncio.CancelledError:
                raise
            except Exception as error:  # noqa: BLE001 - reported, then retried
                self._status(active=False, error=f"{type(error).__name__}: {error}")
                print(f"elosern-map-editor: file following failed ({error}); retrying", file=sys.stderr, flush=True)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_retry)

    async def _watch(self, plan: WatchPlan) -> None:
        """Watch one plan until it changes; reconcile after every batch."""

        settle_ms = max(1, int(self.service.config.settle_seconds * 1000))
        stop = asyncio.Event()
        trigger = asyncio.Event()
        loops: list[tuple[tuple[str, ...], bool, Any]] = []
        if plan.recursive:
            loops.append((plan.recursive, True, watchfiles.DefaultFilter()))
        if plan.flat:
            loops.append((plan.flat, False, flat_filter(plan.targets)))
        established = [False] * len(loops)

        async def loop(index: int, paths, recursive: bool, watch_filter) -> None:
            async for changes in self._awatch(
                *paths,
                watch_filter=watch_filter,
                debounce=DEBOUNCE_MS,
                step=settle_ms,
                stop_event=stop,
                rust_timeout=IDLE_TIMEOUT_MS,
                yield_on_timeout=True,
                recursive=recursive,
                ignore_permission_denied=True,
            ):
                if changes:
                    trigger.set()
                elif not established[index]:
                    # The first idle timeout proves the watcher is running:
                    # reconcile once to close the gap since the last read.
                    established[index] = True
                    if all(established):
                        trigger.set()
            raise RuntimeError("the directory watcher stopped")

        tasks = [asyncio.create_task(loop(i, *spec)) for i, spec in enumerate(loops)]
        waiter: asyncio.Task | None = None
        try:
            while True:
                waiter = asyncio.create_task(trigger.wait())
                await asyncio.wait([waiter, *tasks], return_when=asyncio.FIRST_COMPLETED)
                for task in tasks:
                    if task.done():
                        task.result()  # re-raises the watcher's failure
                trigger.clear()
                try:
                    await self.service.follow()
                except Exception as error:  # noqa: BLE001 - reported; the next batch rereads
                    # A failed reread is not a watcher failure: keep watching.
                    self._status(error=f"reconcile failed: {type(error).__name__}: {error}")
                    continue
                with self.service._state:
                    self.service.following["batches"] += 1
                    self.service.following.update(active=True, error=None)
                # Plan computation reads the reference context: off the loop.
                if await asyncio.to_thread(self.plan) != plan:
                    return
        finally:
            stop.set()
            if waiter is not None:
                waiter.cancel()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*(t for t in (waiter, *tasks) if t is not None), return_exceptions=True)


__all__ = ["WatchCoordinator", "WatchPlan", "discovery_rules", "flat_filter", "watch_plan"]
