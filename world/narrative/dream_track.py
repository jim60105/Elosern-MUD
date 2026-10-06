"""Server-owned dream-goddess arousal track and the generation-free dream ending.

This module owns the W3 dream-explicit-presentation boundary that the durable
six-exchange accounting deliberately leaves to the presentation capability: the
deterministic, session-only pleasure/arousal/climax track of the dream's
goddess counterpart (one collaborative dream conversation), and the
deterministic ending that closes it. The counter advances the *goddess's*
excitement — her climax (reached at the six-exchange convergence) ends the
dream; the player's own live sexual state is never involved.

The track is a pure read model over the durable exchange count owned by
:mod:`world.narrative.dream_session`. It is *not* a live ``SexualState``
handler: it never writes persistent traits, the pleasure gauge, sensitivity,
virginity/experience, lifetime counters, ``climax_today``, buffs, skill
advancement, codex unlocks, or relationship state, and the deterministic sleep
settlement remains the sole physical-restoration path. The only sexual-state
input is the canonical, read-only band table (``PLEASURE_CONFIG``) and the
vocabulary tuples in :mod:`world.lore.sexual_vocab`; no handler instance is
created, read, or mutated, so every operation works with all generation
services offline.

Track semantics (design section 6.4)
------------------------------------

- :data:`INITIAL_PLEASURE` is the committed starting value and
  :data:`EXCHANGE_DELTAS` holds exactly one configured delta per exchange, so
  exchange *N* raises pleasure to ``INITIAL_PLEASURE + sum(deltas[:N])``,
  clamped to the canonical gauge ceiling. The deltas are calibrated to traverse
  the five canonical ``AROUSAL_LEVELS`` bands in order and to reach
  ``climax_phase`` at convergence.
- :func:`track_state` renders the state *after* one given completed count and
  :func:`prospective_state` renders the state the next exchange will commit.
  Both are pure functions of the count, so a retry, a duplicate settlement, a
  transport failure, or an abandoned turn reuses the same phase: the generated
  response can never advance the track and no failure can double-increment it.
- :func:`progression_report` is the committed configuration evidence: one row
  per exchange with the pleasure value, canonical level and climax phase.
- :func:`render_ending` is generation-free. When the track reached climax it
  renders the canonical post-climax phase before fading; an earlier exit fades
  without forcing a climax. Awakening always remains possible.

This module imports nothing from ``world.ai`` and opens no transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS
from world.narrative.dream_session import CONVERGENCE_EXCHANGE, MAX_EXCHANGES
from world.rules.sexual_state.pleasure import PLEASURE_CONFIG

# The versioned track configuration. Version and deltas are committed evidence:
# a change to any of them is a new version, not an in-place edit.
TRACK_VERSION = 1
INITIAL_PLEASURE = 0
EXCHANGE_DELTAS: tuple[int, ...] = (14, 18, 20, 14, 20, 14)
MAX_PLEASURE = PLEASURE_CONFIG.bands[-1].ceiling

# The three exchange modes the presentation capability distinguishes.
MODE_EXCHANGE = "exchange"
MODE_CONVERGENCE = "convergence"
MODE_SUMMARY = "summary"

# Canonical climax-phase labels, indexed by the documented vocabulary order.
CLIMAX_NOT_REACHED = CLIMAX_PHASE_LEVELS[0]
CLIMAX_APPROACHING = CLIMAX_PHASE_LEVELS[1]
CLIMAX_ONGOING = CLIMAX_PHASE_LEVELS[2]
CLIMAX_AFTERGLOW = CLIMAX_PHASE_LEVELS[3]

# The ordinal of the top canonical arousal band (極限) and of the band that
# precedes it (高度); climax eligibility is gated on convergence plus the band.
_TOP_BAND_ORDINAL = len(AROUSAL_LEVELS) - 1
_NEAR_BAND_ORDINAL = _TOP_BAND_ORDINAL - 1


class DreamTrackError(Exception):
    """Base exception for the dream arousal track."""


class DreamTrackRangeError(DreamTrackError):
    """Raised when an exchange count is outside the six-exchange budget."""


@dataclass(frozen=True)
class DreamTrackState:
    """One deterministic view of the session-only dream track."""

    version: int
    completed: int
    pleasure: int
    level: str
    ordinal: int
    climax_phase: str
    converging: bool

    @property
    def climax_reached(self) -> bool:
        """True when the track is in the canonical ongoing-climax phase."""
        return self.climax_phase == CLIMAX_ONGOING


@dataclass(frozen=True)
class DreamProgressionStep:
    """One committed row of the track's progression report."""

    exchange_number: int
    pleasure: int
    level: str
    climax_phase: str


@dataclass(frozen=True)
class DreamEnding:
    """The deterministic, generation-free ending of a dream session.

    ``phase`` is the canonical climax-phase label the ending presents: the
    post-climax phase when the track reached climax, otherwise the track's own
    phase (so an early exit fades without forcing a climax). ``fades`` and
    ``awakens`` are the presentation affordances; awakening never depends on a
    model call.
    """

    version: int
    completed: int
    climax_reached: bool
    phase: str
    fades: bool = True
    awakens: bool = True


def _require_completed(completed: Any, *, prospective: bool) -> int:
    """Validate an exchange count inside the six-exchange budget."""
    if isinstance(completed, bool) or not isinstance(completed, int):
        raise DreamTrackRangeError(f"exchange count must be an int, got {completed!r}")
    upper = MAX_EXCHANGES - 1 if prospective else MAX_EXCHANGES
    if not 0 <= completed <= upper:
        raise DreamTrackRangeError(
            f"exchange count {completed} is outside the budget 0..{upper}"
        )
    return completed


def _pleasure_for(completed: int) -> int:
    value = INITIAL_PLEASURE
    for delta in EXCHANGE_DELTAS[:completed]:
        value = min(value + delta, MAX_PLEASURE)
    return value


def _climax_phase_for(ordinal: int, completed: int) -> str:
    converging = completed + 1 >= CONVERGENCE_EXCHANGE
    if converging and ordinal >= _TOP_BAND_ORDINAL:
        return CLIMAX_ONGOING
    if converging and ordinal >= _NEAR_BAND_ORDINAL:
        return CLIMAX_APPROACHING
    return CLIMAX_NOT_REACHED


def track_state(completed: Any) -> DreamTrackState:
    """Render the deterministic track state after one completed count."""
    locked = _require_completed(completed, prospective=False)
    pleasure = _pleasure_for(locked)
    ordinal = PLEASURE_CONFIG.ordinal_for(pleasure)
    return DreamTrackState(
        version=TRACK_VERSION,
        completed=locked,
        pleasure=pleasure,
        level=AROUSAL_LEVELS[ordinal],
        ordinal=ordinal,
        climax_phase=_climax_phase_for(ordinal, locked),
        converging=locked + 1 >= CONVERGENCE_EXCHANGE,
    )


def prospective_state(completed: Any) -> DreamTrackState:
    """Render the phase the next exchange commits, without committing it.

    The value is a pure function of the durable count, so validation retries
    and duplicate deliveries reuse exactly this phase and the generated
    response cannot advance the track.
    """
    locked = _require_completed(completed, prospective=True)
    return track_state(locked + 1)


def exchange_mode(completed: Any) -> str:
    """Which presentation mode the next exchange uses.

    Exchange five begins convergence and exchange six summarizes the
    spoiler-free direction with no new question.
    """
    locked = _require_completed(completed, prospective=True)
    upcoming = locked + 1
    if upcoming >= MAX_EXCHANGES:
        return MODE_SUMMARY
    if upcoming >= CONVERGENCE_EXCHANGE:
        return MODE_CONVERGENCE
    return MODE_EXCHANGE


def progression_report() -> tuple[DreamProgressionStep, ...]:
    """The committed per-exchange progression evidence (one row per exchange)."""
    rows: list[DreamProgressionStep] = []
    for step in range(1, MAX_EXCHANGES + 1):
        state = track_state(step)
        rows.append(
            DreamProgressionStep(
                exchange_number=step,
                pleasure=state.pleasure,
                level=state.level,
                climax_phase=state.climax_phase,
            )
        )
    return tuple(rows)


def render_ending(completed: Any) -> DreamEnding:
    """Render the deterministic ending without any model call or generation."""
    state = track_state(completed)
    reached = state.climax_reached
    return DreamEnding(
        version=TRACK_VERSION,
        completed=state.completed,
        climax_reached=reached,
        phase=CLIMAX_AFTERGLOW if reached else state.climax_phase,
    )
