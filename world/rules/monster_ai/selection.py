"""Independent, reproducible softmax sampling over one decision's scores.

Selection is deliberately *not* combat dice. It draws from its own
:class:`random.Random` instance, seeded from the decision's real execution
identity, so the hit, damage and initiative streams are untouched by which
candidate a monster prefers and a replay of the same scope reproduces the same
selection.

The recipe is the authored one:

- candidates are put in canonical order (skill key, normalized target
  identifiers, scale) before any probability is attached to them, so neither
  enumeration order nor the family ring's scope-derived offset can bias the
  draw;
- the softmax subtracts the maximum score before exponentiating, which keeps a
  large but finite score set numerically stable while leaving a dominated
  candidate an ordinary (not special-cased) probability;
- the temperature is ``T = 1.25 - 1.17 * i`` with ``i = intelligence / 100``,
  so a clever variant samples close to its best option and an instinctive one
  samples broadly. Equal scores therefore sample uniformly by construction,
  and a lone candidate is deterministic.

The seed is a versioned SHA-256 digest of the actual execution identity: the
session id, the real round index, the actor's stable id, the actual action-slot
index and the recorded configuration fingerprint. A direct two-argument
inspection has no execution scope, and uses the canonical inspection identity
instead -- an empty session, round zero, slot zero, the actor's stable id and
the decision snapshot's own read-only fingerprint -- so an inspection repeats
while it advances no hidden counter and reads no wall clock, object address,
display name, Python ``hash()`` or unordered container.
"""

from collections.abc import Sequence
from hashlib import sha256
from json import dumps
from math import exp, isfinite
from random import Random

from world.rules.combat.decision_scope import ExecutionScope
from world.rules.monster_ai.utility import MonsterAIStateError, ScoredCandidate

#: The seed-encoding version. Bump it whenever the seed payload changes, so a
#: recorded fingerprint can never be mistaken for a different encoding.
SELECTION_SEED_VERSION = 1
#: The canonical identity a direct inspection's seed is built from.
INSPECTION_SESSION_ID = ""
INSPECTION_ROUND_INDEX = 0
INSPECTION_SLOT_INDEX = 0


def selection_temperature(intelligence: int) -> float:
    """Return the authored sampling temperature of one resolved intelligence.

    The ladder runs from ``1.25`` at intelligence zero to ``0.08`` at one
    hundred, and a value outside ``0..100`` or a non-integer is the typed
    invalid state rather than a silently clamped temperature.
    """
    if (
        isinstance(intelligence, bool)
        or not isinstance(intelligence, int)
        or not 0 <= intelligence <= 100
    ):
        raise MonsterAIStateError(
            f"selection needs a resolved 0..100 intelligence, got {intelligence!r}"
        )
    temperature = 1.25 - 1.17 * (intelligence / 100)
    if not isfinite(temperature) or temperature <= 0:
        raise MonsterAIStateError(f"unusable selection temperature: {temperature!r}")
    return temperature


def selection_seed(
    *,
    session_id: str,
    round_index: int,
    actor_id: str,
    slot_index: int,
    identity_fingerprint: str,
) -> int:
    """Return the versioned digest one decision's selection RNG is seeded from.

    ``identity_fingerprint`` is the recorded configuration fingerprint of a
    real decision and the read-only snapshot fingerprint of an inspection;
    every other field is the actual execution identity. The encoding is a
    canonical JSON list -- fixed field order, no unordered container -- hashed
    with SHA-256 and truncated to its first 128 bits.
    """
    payload = [
        SELECTION_SEED_VERSION,
        session_id,
        int(round_index),
        actor_id,
        int(slot_index),
        identity_fingerprint,
    ]
    encoded = dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return int.from_bytes(sha256(encoded.encode("utf-8")).digest()[:16], "big")


def selection_seed_for(
    *,
    scope: ExecutionScope | None,
    actor_id: str,
    configuration_fingerprint: str,
    snapshot_fingerprint: str,
) -> int:
    """Return the seed of one real decision, or of one direct inspection.

    A real decision seeds from its scope's session, actual round, stable actor
    id, actual action slot and the configuration it was resolved with. An
    inspection has no scope: it seeds from the canonical inspection identity
    with slot zero and the snapshot's own read-only fingerprint, which is what
    makes repeated inspection reproducible while a real round never shares
    another slot's identity.

    ``context_mode`` is deliberately NOT part of the encoded payload: the
    requirement enumerates exactly the five inputs above, and the two modes
    cannot currently collide because their round spaces are disjoint by
    construction -- the session path numbers from its durable
    ``rounds_elapsed + 1``, compression numbers its internal rounds from the
    same base (each of them a real round of that encounter), and a bounded
    ``run_battle`` encounter carries the canonical empty session id instead of
    a durable one. A future change that reuses one round index across the two
    modes must therefore bump :data:`SELECTION_SEED_VERSION` and add the mode
    to the payload rather than rely on this note.
    """
    if scope is None:
        return selection_seed(
            session_id=INSPECTION_SESSION_ID,
            round_index=INSPECTION_ROUND_INDEX,
            actor_id=actor_id,
            slot_index=INSPECTION_SLOT_INDEX,
            identity_fingerprint=snapshot_fingerprint,
        )
    return selection_seed(
        session_id=scope.session_id,
        round_index=scope.round_index,
        actor_id=scope.actor_id,
        slot_index=scope.slot_index,
        identity_fingerprint=configuration_fingerprint,
    )


def canonical_order(
    scored: Sequence[ScoredCandidate],
) -> tuple[ScoredCandidate, ...]:
    """Return the candidates in canonical selection order.

    The order is the skill key, then the candidate's normalized target
    identifiers, then its scale. Every candidate identity is unique within one
    decision, so the order is total and no tie can fall back onto the order the
    candidates happened to be enumerated in.
    """
    return tuple(
        sorted(
            scored,
            key=lambda item: (
                item.identity.skill_key,
                item.identity.target_ids,
                item.identity.scale,
            ),
        )
    )


def softmax_probabilities(
    scores: Sequence[float],
    *,
    temperature: float,
) -> tuple[float, ...]:
    """Return the stable softmax of one score sequence at one temperature.

    The maximum score is subtracted before exponentiating, so a large finite
    score set neither overflows nor underflows the whole distribution away.
    Equal scores give equal probabilities (uniform, for an all-equal set), and
    an empty score set gives an empty distribution. A non-finite score or a
    non-positive/non-finite temperature is the typed invalid state, never a
    silently repaired value.
    """
    if not isfinite(temperature) or temperature <= 0:
        raise MonsterAIStateError(f"unusable selection temperature: {temperature!r}")
    for score in scores:
        if not isfinite(score):
            raise MonsterAIStateError(f"a candidate score is not finite: {score!r}")
    if not scores:
        return ()
    top = max(scores)
    weights = [exp((score - top) / temperature) for score in scores]
    total = sum(weights)
    if not isfinite(total) or total <= 0:
        raise MonsterAIStateError(f"a softmax total is unusable: {total!r}")
    return tuple(weight / total for weight in weights)


def sample_index(
    probabilities: Sequence[float],
    *,
    rng: Random,
) -> int:
    """Return one index sampled from a discrete distribution.

    One uniform draw walks cumulative probability, so an all-equal distribution
    samples uniformly and an injected RNG decides the outcome exactly.
    """
    draw = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if draw < cumulative:
            return index
    return len(probabilities) - 1


def select_candidate(
    scored: Sequence[ScoredCandidate],
    *,
    temperature: float,
    seed: int,
    rng: Random | None = None,
) -> ScoredCandidate:
    """Return the candidate one decision's sampling selects.

    ``scored`` must be nonempty: an empty legal set is the caller's no-action
    boundary, not a selection. ``rng`` is the injectable seam -- production
    passes nothing and gets a private generator seeded from ``seed``, which is
    independent of the combat dice stream.
    """
    if not scored:
        raise ValueError("a selection needs at least one scored candidate")
    ordered = canonical_order(scored)
    probabilities = softmax_probabilities(
        [item.score for item in ordered], temperature=temperature
    )
    generator = Random(seed) if rng is None else rng
    return ordered[sample_index(probabilities, rng=generator)]
