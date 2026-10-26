"""Frozen no-mutation read model for the version-8 services panel.

The services panel (WebClient ``services``) is built exclusively by this
module from canonical guild, quest, shop, wallet, inventory, rank, and merit
state through the existing strict parsers and renderers. It performs no
writes, never materializes a lazy trait/buff/sexual/equipment handler, never
creates the world-clock singleton (it reads only through
``world.rules.clock.read_world_clock``), and never reads ``disguised_stats``.
The top-level ``host`` is display-only reconciliation metadata and never an
availability authority or an action payload field.

Host resolution is per service class: ``guild`` resolves ``GuildStaff``,
``rank`` resolves the ``GuildExamReception`` exam counter and ``shop``
resolves ``Merchant``, each through the same ``resolve_local_service_host``
rule the commands use. Zero or multiple hosts of the class a surface requires
make that surface unavailable; different host classes co-located in one room
are independent and never cross-class ambiguity. A targeted read
(``provider_id``) resolves only the selected NPC: its sections are the
capabilities that NPC carries and no other room provider contributes. The
rank surface never depends on guild staff and never looks up the qualified
persistent host: request availability is independent of the host's attendance
and of the actor's merit (guild-exam-appointment-surface). Every non-null
section carries its provider's dbref, and the top-level ``host`` stays
display-only metadata.

The shop rows describe one viewed party member (services-shop-structured-rows):
the held count and server equipment delta of each stock row, the member's
unequipped sellable copies, and buy/sell enablement for that member with the
party purse (the commander's wallet). Host resolution stays on the acting
puppet's room, and personal inventory is published by ``party_inventory``.

Each surface degrades independently: a corrupt quest log, malformed merchant
stock, or unreadable equipment marks only that surface unavailable while the
remaining surfaces stay healthy. A stable reason code accompanies every
unavailable surface for tests and diagnostics; the wire presenter serializes
the surface as ``null`` per the exact panel schema.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from typeclasses.components import GuildExamReception, GuildStaff, Merchant
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY, ItemPresentation
from world.quests.definitions import QUEST_DEFINITION_REGISTRY, QuestType
from world.quests.describe import (
    describe_deadline,
    describe_objective,
    describe_objective_parts,
    describe_offer_deadline,
    describe_quest_detail,
    describe_reward_parts,
)
from world.quests.runtime import QuestDataError, QuestState, read_records
from world.rules.clock import read_world_clock
from world.rules.economy import TradeError, parse_merchant_stock, shop_is_open_at
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    parse_guild_registration,
    parse_reward_claims,
    resolve_local_service_host,
)
from world.rules.guild_config import get_catalog
from world.rules.guild_offers import (
    BoardAccessError,
    GuildOfferNotFound,
    get_guild_offer,
    list_guild_offers,
)
from world.rules.npc_schedules import interaction_reason
from world.rules.service_gate import REASON_REMOTE, service_available
from world.rules.service_messages import SERVICE_REASON_MESSAGES
from world.rules.targeting import RoomActionContext
from world.rules.equipment import normalized_equipment
from world.rules.party_inventory import (
    EquipmentDelta,
    PartyInventoryViewError,
    equipment_delta,
)
from world.rules.party_scope import (
    PARTY_SCOPE_MESSAGES,
    PURPOSE_ORGANIZE,
    PartyScopeError,
    authorize_member,
    resolve_commander,
)
from world.rules.wallet import read_wallet

# Presentation bounds owned by the services view (equal or below the wire
# limits enforced by web.webclient.presentation.services).
MAX_BOARD_ROWS = 12
MAX_QUEST_ROWS = 12
MAX_STOCK_ROWS = 12
MAX_SELLABLE_ROWS = 12
MAX_QUANTITY = 1000

# The three stable root action IDs this delivery unit registers.
ACTION_REGISTER = "guild.register"
ACTION_ACCEPT = "guild.quest_accept"
ACTION_ABANDON = "guild.quest_abandon"
ACTION_TURNIN = "guild.quest_turnin"
ACTION_EXAM_REQUEST = "guild.exam_request"
EXAM_REQUEST_LABEL = "預約升等考核"
ACTION_BUY = "shop.buy"
ACTION_SELL = "shop.sell"


class ServicesViewError(ValueError):
    """A global prerequisite (world clock or player summary) cannot be read.

    Raised when the whole panel must fall back to the common unavailable form,
    never for a failure confined to one surface.
    """


class ServicesSectionError(ValueError):
    """One surface's canonical data is missing, ambiguous, or malformed.

    ``args[0]`` is the stable reason code; the surface becomes ``null`` in the
    wire payload while the rest of the panel stays available.
    """


@dataclass(frozen=True)
class ActionDescriptorView:
    """One row action preview with deterministic enabled state.

    Attributes:
        action_id: The stable action identifier submitted on activate.
        label: The bounded Traditional Chinese label.
        enabled: Whether the action may be submitted now.
        reason_code: Stable disabled-reason code, or ``None`` when enabled.
        reason_message: Safe disabled explanation, or ``None`` when enabled.
        quantity_min: Positive quantity minimum for buy/sell, else ``None``.
        quantity_max: Server-computed quantity maximum for buy/sell, else ``None``.
    """

    action_id: str
    label: str
    enabled: bool
    reason_code: str | None
    reason_message: str | None
    quantity_min: int | None
    quantity_max: int | None


@dataclass(frozen=True)
class HostView:
    """Display-only reconciliation identity of one resolved local host.

    Never an availability authority and never submitted in an action payload.
    """

    identity: str
    display_name: str


@dataclass(frozen=True)
class PlayerSummaryView:
    """The canonical wallet/registration/rank/merit summary."""

    wallet: int
    guild_registered: bool
    guild_rank: str | None
    guild_merit: int
    next_rank: str | None
    next_threshold: int | None


@dataclass(frozen=True)
class RegistrationView:
    """The registration surface with its register action descriptor."""

    registered: bool
    register: ActionDescriptorView


@dataclass(frozen=True)
class BoardRowView:
    """One bounded board-offer row in deterministic rank/key order."""

    definition_key: str
    display_name: str
    category: QuestType
    objective_summary: str
    objective_note: str | None
    deadline_line: str | None
    rationale: str | None
    flavor: str | None
    reward: dict[str, Any]
    rank: str
    accept: ActionDescriptorView


@dataclass(frozen=True)
class QuestRowView:
    """One bounded quest-log row with full server-rendered detail."""

    quest_id: str
    definition_key: str
    display_name: str
    state: str
    stage_index: int
    stage_progress: int
    objective_summary: str
    deadline_line: str | None
    detail: str
    abandon: ActionDescriptorView
    turnin: ActionDescriptorView
    tracked: bool


@dataclass(frozen=True)
class RankView:
    """The rank/examination surface present only with one local exam counter.

    ``merit_qualified`` reports the true cumulative merit against the next
    threshold; ``exam_request`` is enabled by a valid registered next-rank
    target and a functioning local counter alone. The two are distinct facts
    with no equality constraint.
    """

    rank: str | None
    merit: int
    next_rank: str | None
    next_threshold: int | None
    merit_qualified: bool
    exam_request: ActionDescriptorView
    provider_id: int


@dataclass(frozen=True)
class GuildSectionView:
    """The guild surface (registration, board, quest log) of one staff host.

    The rank surface is independent of guild staff and travels beside this
    section on :class:`ServicesView`.
    """

    provider_id: int
    branch_label: str
    rank_ladder: tuple[str, ...]
    registration: RegistrationView
    board: tuple[BoardRowView, ...]
    quests: tuple[QuestRowView, ...]


@dataclass(frozen=True)
class ViewedFactsView:
    """The viewed member's facts for one stock row.

    ``held`` counts every canonical copy the member carries (worn ones
    included); ``delta`` is the server equipment delta against the member's
    current slot occupant for equipment, and ``None`` for anything else.
    """

    held: int
    delta: EquipmentDelta | None


@dataclass(frozen=True)
class StockRowView:
    """One bounded catalog stock row in catalog offer order (buy price only)."""

    item_key: str
    display_name: str
    presentation: ItemPresentation | None
    buy_copper: int
    stock: int
    max_stock: int
    viewed: ViewedFactsView
    buy: ActionDescriptorView


@dataclass(frozen=True)
class SellableRowView:
    """One of the viewed member's unequipped, offered items (sell price only).

    ``held`` counts the member's unequipped copies only.
    """

    item_key: str
    display_name: str
    presentation: ItemPresentation | None
    sell_copper: int
    held: int
    sell: ActionDescriptorView


@dataclass(frozen=True)
class ShopSectionView:
    """The shop surface (open state, viewed member, stock, sellable rows)."""

    provider_id: int
    open: bool
    member_id: int
    stock: tuple[StockRowView, ...]
    sellable: tuple[SellableRowView, ...]


@dataclass(frozen=True)
class PaginationView:
    """Shipped row counts, one per surface (zero for a null surface)."""

    board_total: int
    quest_total: int
    stock_total: int
    sellable_total: int


@dataclass(frozen=True)
class ServicesView:
    """The complete frozen read-only services presentation inputs.

    The ``*_unavailable_reason`` fields carry stable codes for the surfaces
    that are null; the wire presenter serializes those surfaces as ``null``.
    """

    host: HostView | None
    player: PlayerSummaryView
    guild: GuildSectionView | None
    rank: RankView | None
    shop: ShopSectionView | None
    pagination: PaginationView
    guild_unavailable_reason: str | None = None
    shop_unavailable_reason: str | None = None


def _resolve_host(actor: Any, component_class: type) -> tuple[Any, str | None]:
    """Return ``(host, None)`` or ``(None, stable_reason)`` for one class."""
    try:
        return resolve_local_service_host(actor, component_class), None
    except GuildServiceError as error:
        message = str(error.args[0]) if error.args else ""
        if message == "multiple local service hosts":
            return None, "ambiguous_service_host"
        return None, "no_local_service_host"


def _read_merit(actor: Any) -> int:
    raw = actor.attributes.get("traits", default=None, category="traits")
    if not isinstance(raw, Mapping):
        raise ServicesViewError("trait storage is unavailable")
    trait = raw.get("guild_merit")
    if not isinstance(trait, Mapping):
        raise ServicesViewError("guild_merit is malformed")
    value = trait.get("current", trait.get("base", 0))
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ServicesViewError("guild_merit is malformed")
    return value


def _next_rank_and_threshold(rank_key: str | None, catalog: Any) -> tuple[str | None, int | None]:
    """Return the exact next rank key and its merit threshold, or nulls."""
    if rank_key is None:
        return None, None
    rank = GUILD_RANK_REGISTRY.get(rank_key)
    if rank is None:
        raise ServicesViewError("guild rank is malformed")
    candidate = next(
        (
            member
            for member in GUILD_RANK_REGISTRY.values()
            if member.order == rank.order + 1
        ),
        None,
    )
    if candidate is None:
        return None, None
    return candidate.key, int(catalog.merit_thresholds[candidate.key])


def _build_player(actor: Any, wallet: int, catalog: Any) -> PlayerSummaryView:
    try:
        registered = parse_guild_registration(actor) is not None
    except GuildDataError:
        registered = False
    rank_key = getattr(actor, "guild_rank", None)
    merit = _read_merit(actor)
    next_rank, next_threshold = _next_rank_and_threshold(rank_key, catalog)
    return PlayerSummaryView(
        wallet=wallet,
        guild_registered=registered,
        guild_rank=rank_key,
        guild_merit=merit,
        next_rank=next_rank,
        next_threshold=next_threshold,
    )


def _build_host(staff: Any, merchant_host: Any) -> HostView | None:
    host = staff if staff is not None else merchant_host
    if host is None:
        return None
    return HostView(identity=str(int(host.pk)), display_name=str(host.key))


def _active_definition_keys(records: list[Any]) -> set[str]:
    return {
        record.definition_key
        for record in records
        if record.state is QuestState.IN_PROGRESS
    }


def _offer_for(definition_key: str, registration: Any):
    if registration is None:
        return None
    try:
        return get_guild_offer(definition_key, registration["branch_key"])
    except GuildOfferNotFound:
        return None


def _build_board(
    records: list[Any], offers: tuple[Any, ...]
) -> tuple[BoardRowView, ...]:
    active_definitions = _active_definition_keys(records)
    rows: list[BoardRowView] = []
    for offer in offers:
        definition = QUEST_DEFINITION_REGISTRY.get(offer.definition_key)
        if definition is None:
            continue
        has_active = offer.definition_key in active_definitions
        reason = None if not has_active else "quest_already_active"
        objective_summary, objective_note = describe_objective_parts(definition.stages[0].objective)
        rows.append(
            BoardRowView(
                definition_key=offer.definition_key,
                display_name=definition.display_name,
                category=definition.quest_type,
                objective_summary=objective_summary,
                objective_note=objective_note,
                deadline_line=describe_offer_deadline(definition.deadline_hours),
                rationale=definition.rating_rationale_zh,
                flavor=definition.background_flavor_zh,
                reward=describe_reward_parts(offer.reward),
                rank=definition.rank,
                accept=ActionDescriptorView(
                    action_id=ACTION_ACCEPT,
                    label="接取",
                    enabled=not has_active,
                    reason_code=reason,
                    reason_message=None if reason is None else SERVICE_REASON_MESSAGES[reason],
                    quantity_min=None,
                    quantity_max=None,
                ),
            )
        )
        if len(rows) >= MAX_BOARD_ROWS:
            break
    return tuple(rows)


def _build_quests(
    actor: Any,
    records: list[Any],
    claims: list[str],
    registration: Any,
    tick: int,
) -> tuple[QuestRowView, ...]:
    rows: list[QuestRowView] = []
    for record in records:
        definition = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        if definition is None:
            continue
        offer = _offer_for(record.definition_key, registration)
        state = record.state.value
        stage = definition.stages[record.stage_index]
        claimed = record.quest_id in claims
        abandon_enabled = state == "in_progress"
        turnin_enabled = state == "completed" and not claimed
        if abandon_enabled:
            abandon_reason = None
        else:
            abandon_reason = "quest_transition"
        if turnin_enabled:
            turnin_reason = None
        elif state != "completed":
            turnin_reason = "quest_transition"
        else:
            turnin_reason = "already_claimed"
        rows.append(
            QuestRowView(
                quest_id=record.quest_id,
                definition_key=record.definition_key,
                display_name=definition.display_name,
                state=state,
                stage_index=record.stage_index,
                stage_progress=record.stage_progress,
                objective_summary=describe_objective(stage.objective),
                deadline_line=describe_deadline(record.deadline_tick, tick),
                detail=describe_quest_detail(record, definition, offer, tick),
                abandon=ActionDescriptorView(
                    action_id=ACTION_ABANDON,
                    label="放棄",
                    enabled=abandon_enabled,
                    reason_code=abandon_reason,
                    reason_message=None if abandon_reason is None else SERVICE_REASON_MESSAGES[abandon_reason],
                    quantity_min=None,
                    quantity_max=None,
                ),
                turnin=ActionDescriptorView(
                    action_id=ACTION_TURNIN,
                    label="回報",
                    enabled=turnin_enabled,
                    reason_code=turnin_reason,
                    reason_message=None if turnin_reason is None else SERVICE_REASON_MESSAGES[turnin_reason],
                    quantity_min=None,
                    quantity_max=None,
                ),
                tracked=bool(record.tracked),
            )
        )
        if len(rows) >= MAX_QUEST_ROWS:
            break
    return tuple(rows)


def _read_registration(
    actor: Any,
) -> tuple[Mapping[str, Any] | None, bool]:
    """Return ``(registration, malformed)`` for the rank surface's own read."""
    try:
        return parse_guild_registration(actor), False
    except GuildDataError:
        return None, True


def _exam_request_reason(
    actor: Any,
    counter: Any,
    registration: Mapping[str, Any] | None,
    next_rank: str | None,
    *,
    malformed_registration: bool = False,
) -> str | None:
    """The stable disabled reason of the exam request, or ``None`` when enabled.

    Only the target (registration, exact next rank) and the local counter's
    schedule, service and branch gates count, in the request coordinator's
    own precedence; merit and the qualified host's attendance never disable
    the request.
    """
    if interaction_reason(counter, "service_guild") is not None:
        return "schedule_blocked"
    component = counter.components.get(GuildExamReception.get_component_slot())
    verdict = service_available(actor, counter, component)
    if not verdict.allowed:
        return "remote_examiner" if verdict.reason == REASON_REMOTE else "service_unavailable"
    if malformed_registration:
        return "malformed_registration"
    if registration is None:
        return "unregistered"
    if registration["branch_key"] != component.branch_key:
        return "wrong_branch"
    if next_rank is None:
        return "top_rank"
    return None


def _build_rank(
    actor: Any, counter: Any, catalog: Any
) -> RankView | None:
    """Build the independent rank surface of one exact exam counter.

    Only the counter's presence, schedule, service gate and the actor's own
    registration decide it; guild staff play no part.
    """
    if counter is None:
        return None
    registration, malformed = _read_registration(actor)
    rank_key = getattr(actor, "guild_rank", None)
    merit = _read_merit(actor)
    next_rank, next_threshold = _next_rank_and_threshold(rank_key, catalog)
    merit_qualified = (
        registration is not None and next_rank is not None and merit >= next_threshold
    )
    reason = _exam_request_reason(
        actor,
        counter,
        registration,
        next_rank,
        malformed_registration=malformed,
    )
    return RankView(
        rank=rank_key,
        merit=merit,
        next_rank=next_rank,
        next_threshold=next_threshold,
        merit_qualified=merit_qualified,
        exam_request=ActionDescriptorView(
            action_id=ACTION_EXAM_REQUEST,
            label=EXAM_REQUEST_LABEL,
            enabled=reason is None,
            reason_code=reason,
            reason_message=None if reason is None else SERVICE_REASON_MESSAGES[reason],
            quantity_min=None,
            quantity_max=None,
        ),
        provider_id=int(counter.pk),
    )


def _build_guild(
    actor: Any,
    staff: Any,
    staff_reason: str | None,
    catalog: Any,
    tick: int,
) -> tuple[GuildSectionView | None, str | None]:
    if staff is None:
        return None, staff_reason or "no_local_service_host"
    try:
        registration = parse_guild_registration(actor)
    except GuildDataError:
        return None, "guild_data_error"
    try:
        offers = list_guild_offers(actor, staff)
    except BoardAccessError:
        offers = ()
    except GuildDataError:
        return None, "guild_data_error"
    try:
        records = read_records(actor)
    except QuestDataError:
        return None, "malformed_quest_log"
    try:
        claims = parse_reward_claims(actor)
    except Exception:
        return None, "malformed_quest_log"

    registered = registration is not None
    board = _build_board(records, offers)
    quests = _build_quests(actor, records, claims, registration, tick)
    register_reason = None if not registered else "already_registered"
    section = GuildSectionView(
        provider_id=int(staff.pk),
        branch_label=GUILD_BRANCH_REGISTRY[
            staff.components.get(GuildStaff.get_component_slot()).branch_key
        ].display_name_zh,
        rank_ladder=tuple(
            key for key, rank in sorted(GUILD_RANK_REGISTRY.items(), key=lambda entry: entry[1].order)
        ),
        registration=RegistrationView(
            registered=registered,
            register=ActionDescriptorView(
                action_id=ACTION_REGISTER,
                label="註冊為冒險者",
                enabled=not registered,
                reason_code=register_reason,
                reason_message=None if register_reason is None else SERVICE_REASON_MESSAGES[register_reason],
                quantity_min=None,
                quantity_max=None,
            ),
        ),
        board=board,
        quests=quests,
    )
    return section, None


def _trade_descriptor(
    action_id: str,
    label: str,
    reason: str | None,
    maximum: int,
    *,
    message: str | None = None,
) -> ActionDescriptorView:
    """One buy/sell descriptor; an enabled one advertises ``1..maximum``."""
    enabled = reason is None
    return ActionDescriptorView(
        action_id=action_id,
        label=label,
        enabled=enabled,
        reason_code=reason,
        reason_message=(
            None
            if enabled
            else message if message is not None else SERVICE_REASON_MESSAGES[reason]
        ),
        quantity_min=1 if enabled else None,
        quantity_max=maximum if enabled else None,
    )


def _member_scope(actor: Any, member: Any) -> tuple[str, str] | None:
    """The trade rule's member boundary verdict as ``(code, message)``.

    The same ``authorize_member`` call ``economy.buy``/``economy.sell`` make
    first (organizing purpose, anchored on the acting puppet), so a viewed
    member who is absent or no longer in the party disables every row instead
    of advertising a trade the rule refuses.
    """
    try:
        commander = resolve_commander(actor)
        authorize_member(commander, int(member.pk), PURPOSE_ORGANIZE, anchor=actor)
    except PartyScopeError as error:  # observability: ignore R2: the boundary verdict becomes the disabled descriptor's stable reason; no state or I/O is involved
        return error.reason, PARTY_SCOPE_MESSAGES[error.reason]
    return None


def _member_holdings(member: Any) -> tuple[Counter, dict[str, int]]:
    """The member's canonical copy counts and worn copy counts, read strictly."""
    raw = member.db.inventory
    if raw is None:
        entries: list[str] = []
    elif isinstance(raw, str) or not isinstance(raw, Sequence):
        raise ServicesSectionError("malformed_inventory")
    else:
        entries = list(raw)
    if not all(isinstance(entry, str) for entry in entries):
        raise ServicesSectionError("malformed_inventory")
    equipment = normalized_equipment(member)
    if equipment is None:
        raise ServicesSectionError("malformed_equipment")
    worn: dict[str, int] = {}
    for key in (equipment["weapon_main"], equipment["weapon_off"], equipment["armor"]):
        if key is not None:
            worn[key] = 1
    for key in equipment["accessories"]:
        worn[key] = 1
    return Counter(entries), worn


def _viewed_delta(member: Any, definition: Any, item_key: str) -> EquipmentDelta | None:
    """The member's server equipment delta for equipment, else ``None``."""
    from world.rules.status_query import StatusQueryError

    if definition is None or definition.equipment_slot is None:
        return None
    try:
        return equipment_delta(member, item_key)
    except PartyInventoryViewError as error:
        raise ServicesSectionError("malformed_equipment") from error
    except StatusQueryError as error:
        raise ServicesSectionError("malformed_traits") from error
    except Exception as error:
        # Any other failure of the comparison is confined to the shop
        # surface: guild and the player summary must stay available.
        raise ServicesSectionError("equipment_delta_unavailable") from error


def _build_shop(
    actor: Any,
    member: Any,
    merchant_host: Any,
    merchant_reason: str | None,
    catalog: Any,
    tick: int,
    wallet: int,
) -> tuple[ShopSectionView | None, str | None]:
    """Build the shop rows for ``member`` paying from the party purse ``wallet``.

    Reasons follow the trade rule's refusals for one unit, with the closed
    shop first so a closed shop disables every row with the same reason;
    an enabled descriptor never advertises a trade ``economy.buy`` or
    ``economy.sell`` would refuse.
    """
    if merchant_host is None:
        return None, merchant_reason or "no_local_service_host"
    merchant = merchant_host.components.get(Merchant.get_component_slot())
    if merchant is None:
        return None, "no_merchant"
    shop_key = merchant.shop_key
    config = catalog.shop_configs.get(shop_key)
    if config is None:
        return None, "unknown_shop"
    try:
        open_now = shop_is_open_at(shop_key, tick)
        stock = parse_merchant_stock(merchant)
    except TradeError:
        return None, "malformed_stock"
    try:
        counts, worn = _member_holdings(member)
    except ServicesSectionError as error:
        return None, str(error.args[0])
    scope = _member_scope(actor, member)

    try:
        stock_rows = _stock_rows(member, config, stock, counts, open_now, scope, wallet)
    except ServicesSectionError as error:
        return None, str(error.args[0])
    sellable_rows = _sellable_rows(config, stock, counts, worn, open_now, scope)
    return (
        ShopSectionView(
            provider_id=int(merchant_host.pk),
            open=open_now,
            member_id=int(member.pk),
            stock=stock_rows,
            sellable=sellable_rows,
        ),
        None,
    )


def _stock_rows(
    member: Any,
    config: Any,
    stock: dict[str, int],
    counts: Counter,
    open_now: bool,
    scope: tuple[str, str] | None,
    wallet: int,
) -> tuple[StockRowView, ...]:
    rows: list[StockRowView] = []
    for offer in config.offers:
        item_key = offer.item_key
        definition = ITEM_REGISTRY.get(item_key)
        available = stock.get(item_key, 0)
        message = None
        maximum = 0
        if not open_now:
            reason = "closed"
        elif scope is not None:
            reason, message = scope
        elif definition is None:
            reason = "unknown_item"
        elif not definition.sellable:
            reason = "unsellable"
        elif available <= 0:
            reason = "insufficient_stock"
        elif wallet < offer.buy_copper:
            reason = "insufficient_funds"
        else:
            reason = None
            affordable = wallet // offer.buy_copper if offer.buy_copper > 0 else MAX_QUANTITY
            maximum = min(available, affordable, MAX_QUANTITY)
        rows.append(
            StockRowView(
                item_key=item_key,
                display_name=(
                    definition.display_name_zh if definition is not None else item_key
                ),
                presentation=definition.presentation if definition is not None else None,
                buy_copper=offer.buy_copper,
                stock=available,
                max_stock=offer.max_stock,
                viewed=ViewedFactsView(
                    held=counts.get(item_key, 0),
                    delta=_viewed_delta(member, definition, item_key),
                ),
                buy=_trade_descriptor(ACTION_BUY, "購買", reason, maximum, message=message),
            )
        )
        if len(rows) >= MAX_STOCK_ROWS:
            break
    return tuple(rows)


def _sellable_rows(
    config: Any,
    stock: dict[str, int],
    counts: Counter,
    worn: dict[str, int],
    open_now: bool,
    scope: tuple[str, str] | None,
) -> tuple[SellableRowView, ...]:
    rows: list[SellableRowView] = []
    offer_by_item = {offer.item_key: offer for offer in config.offers}
    for item_key in sorted(counts):
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None or not definition.sellable:
            continue
        offer = offer_by_item.get(item_key)
        if offer is None:
            continue
        # Only unequipped copies are sellable: the planner refuses a removal
        # that would drop a worn key's last held copy.
        unequipped = counts[item_key] - worn.get(item_key, 0)
        if unequipped < 1:
            continue
        remaining_capacity = offer.max_stock - stock.get(item_key, 0)
        message = None
        maximum = 0
        if not open_now:
            reason = "closed"
        elif scope is not None:
            reason, message = scope
        elif remaining_capacity < 1:
            reason = "stock_overflow"
        else:
            reason = None
            maximum = min(unequipped, remaining_capacity, MAX_QUANTITY)
        rows.append(
            SellableRowView(
                item_key=item_key,
                display_name=definition.display_name_zh,
                presentation=definition.presentation,
                sell_copper=offer.sell_copper,
                held=unequipped,
                sell=_trade_descriptor(ACTION_SELL, "販賣", reason, maximum, message=message),
            )
        )
        if len(rows) >= MAX_SELLABLE_ROWS:
            break
    return tuple(rows)


def _carries(npc: Any, component_class: type) -> Any | None:
    """Return ``npc``'s component of the class, or ``None``."""
    components = getattr(npc, "components", None)
    if components is None or not components.has(component_class.name):
        return None
    return components.get(component_class.get_component_slot())


def build_services_view(
    actor: Any, viewed: Any = None, *, provider_id: int | None = None
) -> ServicesView:
    """Build the frozen services view for ``actor`` or raise ``ServicesViewError``.

    ``viewed`` is the session's viewed party member (the presenter resolves
    it through ``resolve_viewed_member``); ``None`` means the commander. It
    chooses only whose facts the shop rows present and never authorizes.

    ``provider_id`` selects one exact NPC: only that NPC's capabilities become
    the guild, rank and shop sections, and no other room provider contributes
    (a capability the selected NPC lacks stays null). It never supplies
    authority — mutations carry their own exact ``npc_id`` — and no room
    provider is ever substituted. Without it the room's single provider per
    class is discovered as before.

    A missing world-clock singleton or an unreadable player summary raises
    ``ServicesViewError`` so the caller can choose the whole-panel unavailable
    form; a failure confined to one surface is recorded as that surface's
    stable reason while the rest of the panel stays healthy. During an active
    combat session the remote service surfaces (host, guild, rank, shop) are
    forced null with zero pagination totals while the canonical player
    summary stays available. Outside combat, a possessed actor omits only the
    guild and rank surfaces: the merchant still resolves normally and the shop
    keeps its ordinary viewed-member rows.
    """
    from world.rules.combat_session import is_in_active_session

    clock = read_world_clock()
    if clock is None:
        raise ServicesViewError("world clock is absent")
    tick = int(clock.tick)
    catalog = get_catalog()
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    owner = None
    if possessed_by is not None:
        from world.rules.possession import _resolve_live_object
        owner = _resolve_live_object(int(possessed_by))

    player_source = owner if owner is not None else actor
    wallet = read_wallet(player_source, ServicesViewError)

    player = _build_player(player_source, wallet, catalog)
    in_combat = is_in_active_session(actor)
    targeted = provider_id is not None
    provider = None
    if targeted:
        from world.rules.service_targets import require_service_provider

        # Identity admission runs for every targeted read, combat included: an
        # unusable selection is rejected, never silently read as an empty
        # snapshot. The caller (``services.open``) owns the rejection result.
        provider = require_service_provider(actor, provider_id)
    if in_combat:
        guild, guild_reason = None, None
        rank = None
        shop, shop_reason = None, None
        host = None
    elif targeted:
        staff = _carries(provider, GuildStaff)
        reception = _carries(provider, GuildExamReception)
        merchant = _carries(provider, Merchant)
        host = _build_host(provider, None)
        if owner is not None:
            guild, guild_reason = None, None
            rank = None
        else:
            guild, guild_reason = _build_guild(
                actor, staff, None, catalog, tick
            )
            rank = _build_rank(actor, reception, catalog)
        shop, shop_reason = _build_shop(
            actor,
            viewed if viewed is not None else actor,
            merchant,
            None,
            catalog,
            tick,
            wallet,
        )
    else:
        merchant_host, merchant_reason = _resolve_host(actor, Merchant)
        if owner is not None:
            guild, guild_reason = None, None
            rank = None
            host = _build_host(None, merchant_host)
        else:
            staff, staff_reason = _resolve_host(actor, GuildStaff)
            reception, _ = _resolve_host(actor, GuildExamReception)
            host = _build_host(staff, merchant_host)
            guild, guild_reason = _build_guild(
                actor, staff, staff_reason, catalog, tick
            )
            rank = _build_rank(actor, reception, catalog)
        shop, shop_reason = _build_shop(
            actor,
            viewed if viewed is not None else actor,
            merchant_host,
            merchant_reason,
            catalog,
            tick,
            wallet,
        )

    return ServicesView(
        host=host,
        player=player,
        guild=guild,
        rank=rank,
        shop=shop,
        pagination=PaginationView(
            board_total=len(guild.board) if guild is not None else 0,
            quest_total=len(guild.quests) if guild is not None else 0,
            stock_total=len(shop.stock) if shop is not None else 0,
            sellable_total=len(shop.sellable) if shop is not None else 0,
        ),
        guild_unavailable_reason=guild_reason,
        shop_unavailable_reason=shop_reason,
    )


__all__ = [
    "ACTION_ABANDON",
    "ACTION_ACCEPT",
    "ACTION_BUY",
    "ACTION_EXAM_REQUEST",
    "EXAM_REQUEST_LABEL",
    "ACTION_REGISTER",
    "ACTION_SELL",
    "ACTION_TURNIN",
    "ActionDescriptorView",
    "BoardRowView",
    "GuildSectionView",
    "HostView",
    "ItemPresentation",
    "MAX_BOARD_ROWS",
    "MAX_QUEST_ROWS",
    "MAX_QUANTITY",
    "MAX_SELLABLE_ROWS",
    "MAX_STOCK_ROWS",
    "PaginationView",
    "PlayerSummaryView",
    "QuestRowView",
    "RankView",
    "RegistrationView",
    "SellableRowView",
    "ServicesSectionError",
    "ServicesView",
    "ServicesViewError",
    "ShopSectionView",
    "StockRowView",
    "ViewedFactsView",
    "build_services_view",
]
