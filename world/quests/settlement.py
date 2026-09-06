"""Pure automatic-settlement planning and commit helpers (quest-auto-settlement).

A record completing under a ``Settlement.AUTO`` issuance pays its immutable
reward (copper and items, never merit) atomically with the completion instead
of waiting for a counter turn-in. One pure planner answers "which completions
pay, and how much"; the three quest-log write paths in
``world.quests.transitions`` commit the plan inside their own transaction
idiom — inside the replacement's own ``transaction.atomic()``, inside the
delta caller's transaction, and as action ``PendingEffect`` values. Payment
appends to the same ``guild_reward_claims`` exactly-once ledger the counter
path uses, so one quest ID can never be paid twice across modes.

The planner performs no write and reads no world clock. An issuance that no
longer resolves degrades silently (the quest still completes, nothing is
paid); a genuinely failing payout write propagates and rolls the completion
back with it (design D2/D3, parent design §6).
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from world.observability import log_info
from world.quests.runtime import QuestState


class AutoSettlementConflictError(RuntimeError):
    """A settlement plan raced an already-present claim identity."""


@dataclass(frozen=True)
class AutoSettlementEntry:
    """One quest's payable reward, derived from its resolved issuance."""

    quest_id: str
    issuer_key: str
    copper: int
    items: tuple[str, ...]


@dataclass(frozen=True)
class AutoSettlementPlan:
    """The reward surfaces of every supplied completion that pays."""

    entries: tuple[AutoSettlementEntry, ...]

    @property
    def wallet_delta(self) -> int:
        return sum(entry.copper for entry in self.entries)

    @property
    def item_additions(self) -> tuple[str, ...]:
        return tuple(key for entry in self.entries for key in entry.items)

    @property
    def claim_ids(self) -> tuple[str, ...]:
        return tuple(entry.quest_id for entry in self.entries)


@dataclass(frozen=True)
class SettlementPlan:
    """Write-path plan: the reward entries plus the ACQUIRE chain they cause.

    ``chain_records`` is the full record list after applying every ACQUIRE
    replacement the paid items trigger against the virtual post-transition
    state (``None`` when the chain changed nothing). ``chain_pins`` are the
    stage-pin releases the chain completions produce. ``inventory_after`` is
    the actor's full inventory list once every paid item has landed (``None``
    when nothing pays).
    """

    entries: tuple[AutoSettlementEntry, ...]
    chain_records: tuple[Any, ...] | None
    chain_pins: tuple[tuple[Any, tuple[str, ...], tuple[str, ...]], ...]
    inventory_after: tuple[str, ...] | None

    @property
    def wallet_delta(self) -> int:
        return sum(entry.copper for entry in self.entries)

    @property
    def item_additions(self) -> tuple[str, ...]:
        return tuple(key for entry in self.entries for key in entry.items)

    @property
    def claim_ids(self) -> tuple[str, ...]:
        return tuple(entry.quest_id for entry in self.entries)


def just_completed_records(
    old_entries: list[Any], new_records: list[Any]
) -> list[Any]:
    """Return the records that transition into COMPLETED at this write boundary.

    The same diff ``_schedule_transition_events`` computes — one notion of
    "just completed" for the whole module (design §6.2). Old stored entries are
    signature-parsed with the strict record reader; a record contributes when
    its state is COMPLETED and the stored entry for its quest ID is absent or
    not yet COMPLETED. A malformed or duplicated stored identity skips the
    whole boundary: settlement never invents a payout from untrusted storage.
    """
    from world.quests.transitions import _record_signature

    before: dict[str, str] = {}
    for entry in old_entries or []:
        signature = _record_signature(entry)
        if signature is None:
            return []
        quest_id = str(entry["quest_id"])
        if quest_id in before:
            return []
        before[quest_id] = signature[1]
    completing: list[Any] = []
    seen: set[str] = set()
    for record in new_records:
        if record.quest_id in seen:
            return []
        seen.add(record.quest_id)
        if record.state is not QuestState.COMPLETED:
            continue
        if before.get(record.quest_id) == QuestState.COMPLETED.value:
            continue
        completing.append(record)
    return completing


def _settlement_entry(record: Any) -> AutoSettlementEntry | None:
    """Return the payable entry for one completing record, or ``None``.

    An unresolvable issuance and a ``COUNTER`` issuance each contribute
    nothing; the malformed-key case cannot occur because ``from_storage``
    already grammar-validates every stored issuer key.
    """
    from world.rules.quest_issuance import Settlement, resolve_issuance

    issuance = resolve_issuance(record.definition_key, record.issuer_key)
    if issuance is None or issuance.settlement is not Settlement.AUTO:
        return None
    reward = issuance.reward
    return AutoSettlementEntry(
        quest_id=record.quest_id,
        issuer_key=record.issuer_key,
        copper=reward.copper,
        items=tuple(
            item.item_key for item in reward.items for _ in range(item.quantity)
        ),
    )


def plan_auto_settlement(
    actor: Any, completed_records: list[Any]
) -> AutoSettlementPlan:
    """Plan the settlement for every supplied record just reached COMPLETED.

    Pure (design D2): performs no write and reads no world clock. A record
    contributes only when its issuance resolves, that issuance's settlement
    mode is ``AUTO``, and its quest ID is absent from the actor's reward-claim
    ledger. Rewards come from the resolved issuance's immutable
    ``QuestReward`` — never from a value stored on the record. A ``COUNTER``
    record, an already-claimed record, and a record whose issuance no longer
    resolves each contribute nothing, the last without raising.
    """
    from world.rules.guild import parse_reward_claims

    claims = set(parse_reward_claims(actor))
    entries = [
        entry
        for record in completed_records
        if record.quest_id not in claims
        and (entry := _settlement_entry(record)) is not None
    ]
    return AutoSettlementPlan(entries=tuple(entries))


def plan_auto_settlement_chain(
    actor: Any, old_entries: list[Any], new_records: list[Any]
) -> SettlementPlan:
    """Write-path planner: the just-completed diff plus the ACQUIRE chain.

    ``just_completed_records`` supplies the paying completions; every paid
    item is then fed to the ACQUIRE runtime against the VIRTUAL
    post-transition record set, so an automatic reward completes another
    active quest exactly as a counter-paid item would — the same acquisition
    carries the same objective semantics under both settlement modes. Chain
    completions under ``AUTO`` issuances join the same plan. The loop
    terminates because every iteration either pays a new quest ID (claim
    identities are unique within one plan) or stops, and a record's state only
    moves forward. The final inventory list is validated once through
    ``plan_inventory_delta`` — no new economy primitive (task 3.4).
    """
    from world.rules.equipment import plan_inventory_delta
    from world.rules.guild import parse_reward_claims
    from .acquire import _compute_acquire_replacement_for

    completing = just_completed_records(old_entries, new_records)
    if not completing:
        return _empty_plan()
    claims = list(parse_reward_claims(actor))
    current = list(new_records)
    entries: list[AutoSettlementEntry] = []
    chain_pins: list[tuple[Any, tuple[str, ...], tuple[str, ...]]] = []
    queue = list(completing)
    settled: set[str] = set()
    while queue:
        record = queue.pop(0)
        if record.quest_id in settled or record.quest_id in claims:
            continue
        entry = _settlement_entry(record)
        if entry is None:
            continue
        entries.append(entry)
        settled.add(record.quest_id)
        claims.append(record.quest_id)
        if not entry.items:
            continue
        replacement = _compute_acquire_replacement_for(actor, current, entry.items)
        if replacement is None:
            continue
        previous_states = {
            candidate.quest_id: candidate.state for candidate in current
        }
        current, pins = replacement
        chain_pins.extend(pins)
        for candidate in current:
            if (
                candidate.state is QuestState.COMPLETED
                and previous_states.get(candidate.quest_id)
                is not QuestState.COMPLETED
                and candidate.quest_id not in settled
            ):
                queue.append(candidate)
    if not entries:
        return _empty_plan()
    inventory_after = plan_inventory_delta(
        actor,
        additions=tuple(key for entry in entries for key in entry.items),
    ).after
    chain_records = None if current == list(new_records) else tuple(current)
    return SettlementPlan(
        entries=tuple(entries),
        chain_records=chain_records,
        chain_pins=tuple(chain_pins),
        inventory_after=inventory_after,
    )


def _empty_plan() -> SettlementPlan:
    return SettlementPlan(entries=(), chain_records=None, chain_pins=(), inventory_after=None)


def _merge_claims(actor: Any, claim_ids: tuple[str, ...]) -> None:
    """Append the plan's claim identities to the current ledger, exactly once."""
    from world.rules.guild import parse_reward_claims, write_reward_claims

    claims = parse_reward_claims(actor)
    overlap = [quest_id for quest_id in claim_ids if quest_id in claims]
    if overlap:
        raise AutoSettlementConflictError(
            f"quest ids {overlap} are already claimed; refusing to pay twice"
        )
    write_reward_claims(actor, [*claims, *claim_ids])


def _emit_settlement_events(actor: Any, plan: AutoSettlementPlan) -> None:
    """Register one settlement boundary event per payout on the outermost commit.

    Fired through ``transaction.on_commit`` like every quest boundary event:
    discarded on rollback, so a rolled-back settlement never leaves a payout
    line behind. An empty plan registers nothing (task 4.1).
    """
    for entry in plan.entries:
        transaction.on_commit(
            lambda entry=entry, actor=actor: log_info(
                "quest_auto_settlement",
                context={
                    "char": str(actor.pk),
                    "quest": entry.quest_id,
                    "issuer": entry.issuer_key,
                    "copper": entry.copper,
                    "items": list(entry.items),
                },
            )
        )


def commit_auto_settlement(actor: Any, plan: SettlementPlan) -> None:
    """Commit one plan's wallet, inventory, and claim writes.

    Shared by the replacement and delta write paths inside their owning
    transaction; a no-op for an empty plan. A conflicting claim identity
    raises so the surrounding transaction rolls the completion back together
    with the payout — never complete-but-unpaid, never paid-but-not-complete.
    """
    if not plan.entries:
        return
    actor.db.wallet = int(actor.db.wallet or 0) + plan.wallet_delta
    actor.db.inventory = list(plan.inventory_after)
    _merge_claims(actor, plan.claim_ids)
    _emit_settlement_events(actor, plan)


def settlement_pending_effect(actor: Any, plan: SettlementPlan) -> Any | None:
    """Expose one plan as an action ``PendingEffect`` (task 3.3).

    One effect carries the union of the three settlement surfaces so the
    resolver snapshots them together, and the apply re-checks claim
    eligibility before writing: all three surfaces land together, or the
    commit fails and the action rolls back with the completion it earned.
    Returns ``None`` for an empty plan — nothing is staged, nothing is
    snapshotted.
    """
    if not plan.entries:
        return None
    from world.rules.action import PendingEffect

    def _apply() -> None:
        _merge_claims(actor, plan.claim_ids)
        actor.db.wallet = int(actor.db.wallet or 0) + plan.wallet_delta
        actor.db.inventory = list(plan.inventory_after)
        _emit_settlement_events(actor, plan)

    return PendingEffect(
        actor,
        f"auto_settlement|{actor.pk}",
        frozenset({"wallet", "inventory", "reward_claims"}),
        _apply,
    )
