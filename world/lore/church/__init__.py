"""Frozen Light Church lore catalogues (design 2026-09-22 §4.2).

Two frozen-dataclass registry shells, validated at import exactly like every
other lore registry in this package:

- :data:`OFFERING_CATALOG` — the sexual-ministry offering rows
  ``{key, act_key, merit, copper, min_lineage?}``. Seeds ship for the act
  keys that are currently ownable at character creation (the ``unlock={}``,
  non-``ownership_gated`` seed acts of the solo/partner/shame lines); they
  stay inert until ``implement-church-accrual`` wires the offering rail. A
  ``copper`` of ``None`` means the offering pays the rulebook band default
  (``church.yaml`` ``offering_payout_band``).
- :data:`REDEEM_CATALOG` — the ordination redemption rows
  ``{skill_key, merit_price, tier, prereq_keys, polarity}``, a VALIDATED
  EMPTY shell: the 16 Series A/B/D rows and their price finals arrive with
  ``implement-church-redemption`` (Series C/E with the order-catalogue
  change). Placeholder prices are forbidden — the row validator rejects
  ``merit_price <= 0``.

Registry resolution (``act_key`` against the sexual-act catalogue,
``saintess_vessel`` never in the redemption catalogue) is proven by the
data-contract tests in ``world/lore/tests/test_church.py``; this module
stays import-light (stdlib only) so the lore package never inverts the
dependency direction toward ``world.skills``.
"""

from dataclasses import dataclass

#: Closed redemption-tier vocabulary (design §5.6 price bands).
REDEEM_TIERS = ("entry", "mid", "high")

#: Closed polarity vocabulary (design §5.5 Series A/D vs B/C ordering).
REDEEM_POLARITIES = ("passive", "active")


class ChurchLoreError(ValueError):
    """A church catalogue row violates the frozen-registry load rules."""


@dataclass(frozen=True)
class OfferingRow:
    """One selectable sexual-ministry offering (design §4.2).

    ``act_key`` projects from the sexual-act catalogue; the row is selectable
    iff the offering character owns that act. ``copper`` is the per-row
    payout override; ``None`` defers to the rulebook band. ``min_lineage`` is
    an optional authored lineage requirement (not a default; no row may carry
    it and a bare ``None`` simultaneously mean different things).
    """

    key: str
    act_key: str
    merit: int
    copper: int | None = None
    min_lineage: str | None = None


@dataclass(frozen=True)
class RedeemRow:
    """One ordination redemption entry (design §4.2/§5.6).

    ``prereq_keys`` reference catalogue-internal keys ONLY — never lineage
    machinery; ``polarity`` is the closed ``passive``/``active`` vocabulary
    the rulebook polarity gate classifies.
    """

    skill_key: str
    merit_price: int
    tier: str
    prereq_keys: tuple[str, ...] = ()
    polarity: str = "active"


def _require_text(value: object, what: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChurchLoreError(f"{what} must be a non-empty string")
    return value


def validate_offering_rows(rows: tuple[OfferingRow, ...]) -> None:
    """Fail closed on malformed offering rows, naming the row.

    Shape only (key/act_key/merit/copper/min_lineage discipline and key
    uniqueness); act-key resolution against the sexual-act catalogue is the
    data-contract tests' job so this module stays dependency-light.
    """
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, OfferingRow):
            raise ChurchLoreError(f"offering row {row!r} is not an OfferingRow")
        _require_text(row.key, f"offering row {row.key!r} key")
        if row.key in seen:
            raise ChurchLoreError(f"duplicate offering row key {row.key!r}")
        seen.add(row.key)
        _require_text(row.act_key, f"offering {row.key!r} act_key")
        if isinstance(row.merit, bool) or not isinstance(row.merit, int) or row.merit < 1:
            raise ChurchLoreError(f"offering {row.key!r} merit must be a positive integer")
        if row.copper is not None and (
            isinstance(row.copper, bool) or not isinstance(row.copper, int) or row.copper < 0
        ):
            raise ChurchLoreError(
                f"offering {row.key!r} copper must be a non-negative integer or None"
            )
        if row.min_lineage is not None:
            _require_text(row.min_lineage, f"offering {row.key!r} min_lineage")


def validate_redeem_rows(rows: tuple[RedeemRow, ...]) -> None:
    """Fail closed on malformed redemption rows, naming the row.

    Rejects by name: missing/empty ``skill_key``, a placeholder
    ``merit_price`` (prices are finals — ``<= 0`` is forbidden), an unknown
    ``tier`` or ``polarity``, an empty or non-string ``prereq_keys`` entry, a
    duplicated prereq, and any lineage-flavoured prereq reference
    (catalogue-internal prereqs are plain keys — a ``:``-bearing marker is
    lineage machinery and has no place in this list).
    """
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, RedeemRow):
            raise ChurchLoreError(f"redemption row {row!r} is not a RedeemRow")
        skill_key = _require_text(row.skill_key, f"redemption row {row.skill_key!r} skill_key")
        if skill_key in seen:
            raise ChurchLoreError(f"duplicate redemption skill_key {skill_key!r}")
        seen.add(skill_key)
        if isinstance(row.merit_price, bool) or not isinstance(row.merit_price, int):
            raise ChurchLoreError(
                f"redemption {skill_key!r} merit_price must be an integer"
            )
        if row.merit_price <= 0:
            raise ChurchLoreError(
                f"redemption {skill_key!r} merit_price must be positive "
                "(placeholder prices are forbidden)"
            )
        if row.tier not in REDEEM_TIERS:
            raise ChurchLoreError(
                f"redemption {skill_key!r} has unknown tier {row.tier!r} "
                f"(expected one of {REDEEM_TIERS})"
            )
        if row.polarity not in REDEEM_POLARITIES:
            raise ChurchLoreError(
                f"redemption {skill_key!r} has unknown polarity {row.polarity!r} "
                f"(expected one of {REDEEM_POLARITIES})"
            )
        if not isinstance(row.prereq_keys, tuple):
            raise ChurchLoreError(
                f"redemption {skill_key!r} prereq_keys must be a tuple"
            )
        prereq_seen: set[str] = set()
        for entry in row.prereq_keys:
            if not isinstance(entry, str) or not entry:
                raise ChurchLoreError(
                    f"redemption {skill_key!r} prereq entries must be non-empty strings"
                )
            if ":" in entry or "lineage" in entry:
                raise ChurchLoreError(
                    f"redemption {skill_key!r} prereq {entry!r} references "
                    "lineage machinery; prereqs are catalogue-internal keys only"
                )
            if entry in prereq_seen:
                raise ChurchLoreError(
                    f"redemption {skill_key!r} prereq {entry!r} is duplicated"
                )
            prereq_seen.add(entry)


#: The shipped offering rows: seed rows for the currently-ownable act keys
#: (the ``unlock={}``, non-``ownership_gated`` seed acts of the solo, partner
#: and shame lines — see the act catalogue, which is the single source of
#: what a fresh character owns). They stay inert until
#: ``implement-church-accrual`` wires the offering rail; ``copper: None``
#: defers each payout to the ``church.yaml`` band default.
OFFERING_CATALOG: tuple[OfferingRow, ...] = (
    OfferingRow(
        key="offering_solo_self_touch",
        act_key="solo_self_touch",
        merit=5,
        copper=None,
    ),
    OfferingRow(
        key="offering_solo_fondle_breasts",
        act_key="solo_fondle_breasts",
        merit=5,
        copper=None,
    ),
    OfferingRow(
        key="offering_solo_thigh_rub",
        act_key="solo_thigh_rub",
        merit=4,
        copper=None,
    ),
    OfferingRow(
        key="offering_partner_caress",
        act_key="partner_caress",
        merit=6,
        copper=None,
    ),
    OfferingRow(
        key="offering_partner_hand_hold",
        act_key="partner_hand_hold",
        merit=2,
        copper=None,
    ),
    OfferingRow(
        key="offering_shame_hem_lift",
        act_key="shame_hem_lift",
        merit=6,
        copper=None,
    ),
)

#: The validated EMPTY redemption shell. The 16 Series A/B/D rows and their
#: price finals land with ``implement-church-redemption`` (Series C/E with
#: the order-catalogue change); nothing ships a placeholder price.
REDEEM_CATALOG: tuple[RedeemRow, ...] = ()

validate_offering_rows(OFFERING_CATALOG)
validate_redeem_rows(REDEEM_CATALOG)

__all__ = [
    "ChurchLoreError",
    "OfferingRow",
    "RedeemRow",
    "REDEEM_TIERS",
    "REDEEM_POLARITIES",
    "OFFERING_CATALOG",
    "REDEEM_CATALOG",
    "validate_offering_rows",
    "validate_redeem_rows",
]