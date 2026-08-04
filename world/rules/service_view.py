"""Frozen no-mutation read model for the version-1 services panel.

The services panel (WebClient ``services``) is built exclusively by this
module from canonical guild, quest, shop, wallet, inventory, rank, and merit
state through the existing strict parsers and renderers. It performs no
writes, never materializes a lazy trait/buff/sexual/equipment handler, never
creates the world-clock singleton (it reads only through
``world.rules.clock.read_world_clock``), and never reads ``disguised_stats``.
The top-level ``host`` is display-only reconciliation metadata and never an
availability authority or an action payload field.

Host resolution is per service class: ``guild``/``rank`` resolve ``GuildStaff``
and ``GuildExaminer`` respectively and ``shop`` resolves ``Merchant``, each
through the same ``resolve_local_service_host`` rule the commands use. Zero or
multiple hosts of the class a surface requires make that surface unavailable;
different host classes co-located in one room are independent and never
cross-class ambiguity.

Each surface degrades independently: a corrupt quest log, malformed merchant
stock, or unreadable equipment marks only that surface unavailable while the
remaining surfaces stay healthy. A stable reason code accompanies every
unavailable surface for tests and diagnostics; the wire presenter serializes
the surface as ``null`` per the exact panel schema.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.describe import (
    describe_deadline,
    describe_objective,
    describe_quest_detail,
    describe_reward,
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
from world.rules.service_messages import SERVICE_REASON_MESSAGES
from world.skills.equipment import list_items

# Presentation bounds owned by the services view (equal or below the wire
# limits enforced by web.webclient.presentation.services).
MAX_BOARD_ROWS = 12
MAX_QUEST_ROWS = 12
MAX_STOCK_ROWS = 12
MAX_SELLABLE_ROWS = 12
MAX_INVENTORY_ROWS = 32
MAX_QUANTITY = 1000

# The three stable root action IDs this delivery unit registers.
ACTION_REGISTER = "guild.register"
ACTION_ACCEPT = "guild.quest_accept"
ACTION_ABANDON = "guild.quest_abandon"
ACTION_TURNIN = "guild.quest_turnin"
ACTION_EXAM_START = "guild.exam_start"
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
    objective_summary: str
    reward_summary: str
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


@dataclass(frozen=True)
class RankView:
    """The rank/examination surface present only with one local examiner."""

    rank: str | None
    merit: int
    next_rank: str | None
    next_threshold: int | None
    eligible: bool
    exam_start: ActionDescriptorView


@dataclass(frozen=True)
class GuildSectionView:
    """The guild surface (registration, board, quest log, rank)."""

    registration: RegistrationView
    board: tuple[BoardRowView, ...]
    quests: tuple[QuestRowView, ...]
    rank: RankView | None


@dataclass(frozen=True)
class StockRowView:
    """One bounded catalog stock row in catalog offer order."""

    item_key: str
    display_name: str
    buy_copper: int
    sell_copper: int
    stock: int
    max_stock: int
    buy: ActionDescriptorView


@dataclass(frozen=True)
class SellableRowView:
    """One bounded held-and-offered sellable row in deterministic order."""

    item_key: str
    display_name: str
    sell_copper: int
    held: int
    sell: ActionDescriptorView


@dataclass(frozen=True)
class ShopSectionView:
    """The shop surface (open state, stock, sellable inventory)."""

    open: bool
    stock: tuple[StockRowView, ...]
    sellable: tuple[SellableRowView, ...]


@dataclass(frozen=True)
class InventoryRowView:
    """One aggregated repeated-key inventory row."""

    item_key: str
    display_name: str
    held: int
    equipped: bool


@dataclass(frozen=True)
class InventorySectionView:
    """The personal inventory surface (aggregated rows plus wallet)."""

    rows: tuple[InventoryRowView, ...]
    wallet: int


@dataclass(frozen=True)
class PaginationView:
    """Shipped row counts, one per surface (zero for a null surface)."""

    board_total: int
    quest_total: int
    stock_total: int
    sellable_total: int
    inventory_total: int


@dataclass(frozen=True)
class ServicesView:
    """The complete frozen read-only services presentation inputs.

    The ``*_unavailable_reason`` fields carry stable codes for the surfaces
    that are null; the wire presenter serializes those surfaces as ``null``.
    """

    host: HostView | None
    player: PlayerSummaryView
    guild: GuildSectionView | None
    shop: ShopSectionView | None
    inventory: InventorySectionView | None
    pagination: PaginationView
    guild_unavailable_reason: str | None = None
    shop_unavailable_reason: str | None = None
    inventory_unavailable_reason: str | None = None


def _resolve_host(actor: Any, component_class: type) -> tuple[Any, str | None]:
    """Return ``(host, None)`` or ``(None, stable_reason)`` for one class."""
    try:
        return resolve_local_service_host(actor, component_class), None
    except GuildServiceError as error:
        message = str(error.args[0]) if error.args else ""
        if message == "multiple local service hosts":
            return None, "ambiguous_service_host"
        return None, "no_local_service_host"


def _read_wallet(actor: Any) -> int:
    raw = actor.db.wallet
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ServicesViewError("wallet is malformed")
    return raw


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
        rows.append(
            BoardRowView(
                definition_key=offer.definition_key,
                display_name=definition.display_name,
                objective_summary=describe_objective(definition.stages[0].objective),
                reward_summary=describe_reward(offer),
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
            )
        )
        if len(rows) >= MAX_QUEST_ROWS:
            break
    return tuple(rows)


def _build_rank(actor: Any, examiner: Any, catalog: Any) -> RankView | None:
    if examiner is None:
        return None
    rank_key = getattr(actor, "guild_rank", None)
    merit = _read_merit(actor)
    next_rank, next_threshold = _next_rank_and_threshold(rank_key, catalog)

    from world.rules.combat_session import is_in_active_session

    active_session = is_in_active_session(actor)
    registered = rank_key is not None
    eligible = (
        registered
        and next_rank is not None
        and merit >= next_threshold
        and not active_session
    )
    if not registered:
        reason = "unregistered"
    elif next_rank is None:
        reason = "already_settled"
    elif merit < next_threshold:
        reason = "below_threshold"
    elif active_session:
        reason = "active_combat"
    else:
        reason = None
    label = f"升階考核（{next_rank}）" if next_rank is not None else "升階考核"
    return RankView(
        rank=rank_key,
        merit=merit,
        next_rank=next_rank,
        next_threshold=next_threshold,
        eligible=eligible,
        exam_start=ActionDescriptorView(
            action_id=ACTION_EXAM_START,
            label=label,
            enabled=eligible,
            reason_code=reason,
            reason_message=None if reason is None else SERVICE_REASON_MESSAGES[reason],
            quantity_min=None,
            quantity_max=None,
        ),
    )


def _build_guild(
    actor: Any,
    staff: Any,
    staff_reason: str | None,
    examiner: Any,
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
    rank = _build_rank(actor, examiner, catalog)
    register_reason = None if not registered else "already_registered"
    section = GuildSectionView(
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
        rank=rank,
    )
    return section, None


def _build_shop(
    actor: Any,
    merchant_host: Any,
    merchant_reason: str | None,
    catalog: Any,
    tick: int,
    wallet: int,
) -> tuple[ShopSectionView | None, str | None]:
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

    stock_rows: list[StockRowView] = []
    for offer in config.offers:
        item_key = offer.item_key
        held = stock.get(item_key, 0)
        affordable = wallet >= offer.buy_copper
        enabled = open_now and held > 0 and affordable
        if enabled:
            reason = None
            maximum = min(held, wallet // offer.buy_copper, MAX_QUANTITY)
        elif not open_now:
            reason = "closed"
        elif held <= 0:
            reason = "insufficient_stock"
        else:
            reason = "insufficient_funds"
        stock_rows.append(
            StockRowView(
                item_key=item_key,
                display_name=ITEM_REGISTRY[item_key].display_name_zh,
                buy_copper=offer.buy_copper,
                sell_copper=offer.sell_copper,
                stock=held,
                max_stock=offer.max_stock,
                buy=ActionDescriptorView(
                    action_id=ACTION_BUY,
                    label="購買",
                    enabled=enabled,
                    reason_code=reason,
                    reason_message=None if reason is None else SERVICE_REASON_MESSAGES[reason],
                    quantity_min=1 if enabled else None,
                    quantity_max=maximum if enabled else None,
                ),
            )
        )
        if len(stock_rows) >= MAX_STOCK_ROWS:
            break

    sellable_rows: list[SellableRowView] = []
    offer_by_item = {offer.item_key: offer for offer in config.offers}
    held_counts = Counter(list_items(actor))
    for item_key in sorted(held_counts):
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None or not definition.sellable:
            continue
        offer = offer_by_item.get(item_key)
        if offer is None:
            continue
        held = held_counts[item_key]
        cap_full = stock.get(item_key, 0) >= offer.max_stock
        enabled = open_now and held >= 1 and not cap_full
        if enabled:
            reason = None
            remaining_capacity = offer.max_stock - stock.get(item_key, 0)
            maximum = min(held, remaining_capacity, MAX_QUANTITY)
        elif not open_now:
            reason = "closed"
        elif held < 1:
            reason = "insufficient_items"
        else:
            reason = "stock_overflow"
        sellable_rows.append(
            SellableRowView(
                item_key=item_key,
                display_name=definition.display_name_zh,
                sell_copper=offer.sell_copper,
                held=held,
                sell=ActionDescriptorView(
                    action_id=ACTION_SELL,
                    label="販賣",
                    enabled=enabled,
                    reason_code=reason,
                    reason_message=None if reason is None else SERVICE_REASON_MESSAGES[reason],
                    quantity_min=1 if enabled else None,
                    quantity_max=maximum if enabled else None,
                ),
            )
        )
        if len(sellable_rows) >= MAX_SELLABLE_ROWS:
            break
    return ShopSectionView(open=open_now, stock=tuple(stock_rows), sellable=tuple(sellable_rows)), None


def _equipped_keys(actor: Any) -> set[str]:
    raw = actor.db.equipment
    if raw is None:
        return set()
    if not isinstance(raw, Mapping):
        raise ServicesSectionError("malformed_equipment")
    keys: list[str] = []
    for slot in ("weapon_main", "weapon_off", "armor"):
        value = raw.get(slot)
        if isinstance(value, str) and value:
            keys.append(value)
    accessories = raw.get("accessories")
    if isinstance(accessories, (list, tuple)):
        keys.extend(str(item) for item in accessories if item)
    return set(keys)


def _build_inventory(
    actor: Any, wallet: int
) -> tuple[InventorySectionView | None, str | None]:
    try:
        items = list_items(actor)
        equipped = _equipped_keys(actor)
    except ServicesSectionError:
        return None, "malformed_equipment"
    counts = Counter(items)
    rows: list[InventoryRowView] = []
    for item_key in sorted(counts):
        definition = ITEM_REGISTRY.get(item_key)
        display_name = definition.display_name_zh if definition is not None else item_key
        rows.append(
            InventoryRowView(
                item_key=item_key,
                display_name=display_name,
                held=counts[item_key],
                equipped=item_key in equipped,
            )
        )
        if len(rows) >= MAX_INVENTORY_ROWS:
            break
    return InventorySectionView(rows=tuple(rows), wallet=wallet), None


def build_services_view(actor: Any) -> ServicesView:
    """Build the frozen services view for ``actor`` or raise ``ServicesViewError``.

    A missing world-clock singleton or an unreadable player summary raises
    ``ServicesViewError`` so the caller can choose the whole-panel unavailable
    form; a failure confined to one surface is recorded as that surface's
    stable reason while the rest of the panel stays healthy.
    """
    clock = read_world_clock()
    if clock is None:
        raise ServicesViewError("world clock is absent")
    tick = int(clock.tick)
    catalog = get_catalog()
    wallet = _read_wallet(actor)

    player = _build_player(actor, wallet, catalog)
    staff, staff_reason = _resolve_host(actor, GuildStaff)
    examiner, _ = _resolve_host(actor, GuildExaminer)
    merchant_host, merchant_reason = _resolve_host(actor, Merchant)
    host = _build_host(staff, merchant_host)

    guild, guild_reason = _build_guild(actor, staff, staff_reason, examiner, catalog, tick)
    shop, shop_reason = _build_shop(actor, merchant_host, merchant_reason, catalog, tick, wallet)
    inventory, inventory_reason = _build_inventory(actor, wallet)

    return ServicesView(
        host=host,
        player=player,
        guild=guild,
        shop=shop,
        inventory=inventory,
        pagination=PaginationView(
            board_total=len(guild.board) if guild is not None else 0,
            quest_total=len(guild.quests) if guild is not None else 0,
            stock_total=len(shop.stock) if shop is not None else 0,
            sellable_total=len(shop.sellable) if shop is not None else 0,
            inventory_total=len(inventory.rows) if inventory is not None else 0,
        ),
        guild_unavailable_reason=guild_reason,
        shop_unavailable_reason=shop_reason,
        inventory_unavailable_reason=inventory_reason,
    )


__all__ = [
    "ACTION_ABANDON",
    "ACTION_ACCEPT",
    "ACTION_BUY",
    "ACTION_EXAM_START",
    "ACTION_REGISTER",
    "ACTION_SELL",
    "ACTION_TURNIN",
    "ActionDescriptorView",
    "BoardRowView",
    "GuildSectionView",
    "HostView",
    "InventoryRowView",
    "InventorySectionView",
    "MAX_BOARD_ROWS",
    "MAX_INVENTORY_ROWS",
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
    "build_services_view",
]
