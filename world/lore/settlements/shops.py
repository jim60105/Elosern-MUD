"""Derived shop identity registry (settlement-shops design §3.2).

Shop identities are a view over the place registry: a place contributes a
``ShopDefinition`` iff its authored kwargs carry a ``shop_key``, and the
derived keys ARE those shop identities — every runtime consumer resolves
``SHOP_REGISTRY[merchant.shop_key]``. The goods a shop stocks are the union
of the assortments its place references (settlement-shops design §3.1).
Exact prices, hours, and stock quantities live in
``world/rules/rulebook/commerce.yaml``. ``world/lore/shops.py`` is deleted;
its two authored-identity validators move here unchanged (their guild
registry imports stay function-local, now absolute for the subpackage move).
"""

from dataclasses import dataclass

from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY


@dataclass(frozen=True)
class ShopDefinition:
    """Immutable identity of one deterministic shop."""

    key: str
    # Authored NPC identity of the shop's service host (design D5).
    host_name: str
    host_title: str
    assortment_keys: tuple[str, ...]

    @property
    def offered_item_keys(self) -> tuple[str, ...]:
        """The derived flat item set: the union of the referenced assortments.

        Assortment membership is the single source of truth; this projection
        exists so consumers (catalog loader, data-contract tests) read the
        same flat view a hand-listed shop used to carry.
        """
        keys: list[str] = []
        seen: set[str] = set()
        for assortment_key in self.assortment_keys:
            for item_key in ASSORTMENT_REGISTRY[assortment_key].item_keys:
                if item_key not in seen:
                    seen.add(item_key)
                    keys.append(item_key)
        return tuple(keys)


def _derive_shop_registry() -> dict[str, ShopDefinition]:
    """Project one ShopDefinition per place that authors a shop identity."""
    registry: dict[str, ShopDefinition] = {}
    for place in PLACE_REGISTRY.values():
        shop_key = dict(place.authored_kwargs).get("shop_key")
        if shop_key is None:
            continue
        if shop_key in registry:
            raise ValueError(
                f"shop_key {shop_key!r} is authored on more than one place: "
                f"{registry[shop_key].key!r} and {place.key!r}"
            )
        registry[shop_key] = ShopDefinition(
            key=shop_key,
            host_name=place.host_name,
            host_title=place.host_title,
            assortment_keys=place.assortment_keys,
        )
    return registry


SHOP_REGISTRY: dict[str, ShopDefinition] = _derive_shop_registry()


def validate_shop_npc_identities(
    definitions: dict[str, ShopDefinition] | None = None,
) -> None:
    """Fail closed on the shipped host authored identities (design D4).

    Pure checker callable with explicit rows (tests); defaults to the shipped
    registry. Raises ValueError naming the offending row and rule.
    """
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    for definition in (SHOP_REGISTRY if definitions is None else definitions).values():
        try:
            validate_npc_name(definition.host_name)
        except ValueError as error:
            raise ValueError(
                f"shop {definition.key} has an invalid host_name: {error}"
            ) from error
        try:
            validate_npc_title(definition.host_title)
        except ValueError as error:
            raise ValueError(
                f"shop {definition.key} has an invalid host_title: {error}"
            ) from error


def validate_registry_identity_uniqueness(
    shop_rows: dict[str, ShopDefinition] | None = None,
    branch_rows: dict[str, object] | None = None,
    rank_rows: dict[str, object] | None = None,
) -> None:
    """Cross-registry authored-name uniqueness over all three name sources (D4).

    Shops, guild branches and guild ranks all name permanent NPC hosts;
    a duplicate authored name across any two of them is a loading error.

    Pure checker callable with explicit rows (tests); each argument defaults
    to its shipped registry. Cycle-safe: the guild registries are imported
    function-locally, so ``guild.py`` can (and does) run the same check
    through this function at its own load time. Raises naming both holders.
    """
    if shop_rows is None:
        shop_rows = SHOP_REGISTRY
    if branch_rows is None or rank_rows is None:
        from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY

        if branch_rows is None:
            branch_rows = GUILD_BRANCH_REGISTRY
        if rank_rows is None:
            rank_rows = GUILD_RANK_REGISTRY
    from world.rules.npc_identity import validate_unique_npc_names

    entries: list[tuple[str, str]] = [
        (f"shop:{definition.key}", definition.host_name)
        for definition in shop_rows.values()
    ]
    entries += [
        (f"guild_branch:{branch.key}", branch.host_name)
        for branch in branch_rows.values()
    ]
    entries += [
        (f"guild_rank:{rank.key}", rank.examiner_name)
        for rank in rank_rows.values()
    ]
    validate_unique_npc_names(entries)


def validate_shipped_identity_uniqueness() -> None:
    """Run the cross-registry uniqueness checker over the shipped rows (D4)."""
    validate_registry_identity_uniqueness()


validate_shop_npc_identities()
validate_shipped_identity_uniqueness()