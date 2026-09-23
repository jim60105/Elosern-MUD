"""Frozen Light Church lore catalogues (design 2026-09-22 §4.2).

Two frozen-dataclass registries, validated at import exactly like every
other lore registry in this package:

- :data:`OFFERING_CATALOG` — the sexual-ministry offering rows
  ``{key, act_key, merit, copper, min_lineage?}``. Seeds ship for the act
  keys that are currently ownable at character creation (the ``unlock={}``,
  non-``ownership_gated`` seed acts of the solo/partner/shame lines), and
  the four advanced Series D ministry rows ``implement-church-redemption``
  lands: their ``act_key`` IS the redemption skill key (``rite_holy_kiss``
  etc.), so the offering projection and the redemption catalogue reference
  the same ``SKILL_REGISTRY`` row with zero duplicated data (design
  §4.2/§5.3, advanced rows). A ``copper`` of ``None`` means the offering
  pays the rulebook band default (``church.yaml`` ``offering_payout_band``).
- :data:`REDEEM_CATALOG` — the ordination redemption rows
  ``{skill_key, merit_price, tier, prereq_keys, polarity}``: the 16
  Series A/B/D rows with their price finals (decide-and-record task 1.1,
  design §5.5/§5.6; Series C/E arrive with the order-catalogue change).
  Placeholder prices are forbidden — the row validator rejects
  ``merit_price <= 0``. Catalogue-internal prereq chains ride the Series D
  high rows only.

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
#: what a fresh character owns) plus the four advanced Series D ministry
#: rows (``act_key`` = the redemption skill key; ``implement-church-
#: redemption`` decided their per-row merits: the ministry acts pay above
#: the seed floor, anointing 8 / milk_blessing 10 / holy_kiss 12 /
#: confession_bed 10). ``copper: None`` defers each payout to the
#: ``church.yaml`` band default.
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
    # Advanced Series D sexual-ministry rows (design §5.5): the same rows
    # serve both catalogues by key — ``act_key`` equals the redemption
    # skill_key, so the offering menu projection and the ordination ladder
    # reference one ``SKILL_REGISTRY`` entry with no duplicated data.
    OfferingRow(
        key="offering_rite_anointing_touch",
        act_key="rite_anointing_touch",
        merit=8,
        copper=None,
    ),
    OfferingRow(
        key="offering_rite_milk_blessing",
        act_key="rite_milk_blessing",
        merit=10,
        copper=None,
    ),
    OfferingRow(
        key="offering_rite_holy_kiss",
        act_key="rite_holy_kiss",
        merit=12,
        copper=None,
    ),
    OfferingRow(
        key="offering_rite_confession_bed",
        act_key="rite_confession_bed",
        merit=10,
        copper=None,
    ),
)

#: The shipped ordination rows — the 16 Series A/B/D price finals
#: (decide-and-record task 1.1 inside the design §5.5 placeholders; Series
#: C/E append with the order-catalogue change). Price bands: entry
#: 300-600, mid 1200-2500, high 4000-8000.
#
#: | Series | skill_key | tier | price | prereqs |
#: | --- | --- | --- | --- | --- |
#: | A | pain_to_pleasure | mid | 1800 | — |
#: | A | priestly_grace | mid | 1500 | — |
#: | A | rapture_renewal | mid | 2200 | — |
#: | A | vow_of_service | entry | 500 | — |
#: | B | rite_heal_light | entry | 400 | — |
#: | B | rite_cleanse | entry | 350 | — |
#: | B | rite_calm | entry | 450 | — |
#: | B | rite_bless_water | entry | 400 | — |
#: | B | rite_sanctify_ground | entry | 550 | — |
#: | B | rite_absolution | entry | 600 | — |
#: | B | rite_lamb_mark | high | 6000 | — |
#: | B | rite_martyrdom_vow | high | 6500 | — |
#: | D | rite_anointing_touch | mid | 1400 | — |
#: | D | rite_milk_blessing | mid | 1800 | — |
#: | D | rite_holy_kiss | high | 4000 | rite_anointing_touch |
#: | D | rite_confession_bed | high | 8000 | rite_holy_kiss |
#: | C | poverty_vow | mid | 1500 | — |
#: | C | obedience | high | 5000 | — |
#: | C | chastity_discipline | entry | 600 | — |
#: | C | temple_endurance | mid | 1800 | — |
#: | C | public_devotion | entry | 500 | — |
#: | E | rite_martial_blessing | mid | 1600 | — |
#: | E | rite_shelter | entry | 450 | — |
#: | E | rite_morning_devotion | mid | 2000 | — |
#
#: Pricing notes: Series A qualifiers price at entry except the three
#: legacy passives (their loop-defining mechanics - damage-to-pleasure
#: conversion, arousal-scaled recovery, climax self-heal - sit at mid);
#: ``vow_of_service`` is a pure ledger-multiplier row priced entry. The six
#: modest rite actives price at entry; the two combat rites (tank-making)
#: at high. The Series D ministry ladder climbs mid -> high through the
#: ONLY catalogue-internal prereq chain in the whole catalogue (anointing
#: touch -> holy kiss -> confession bed), per design §5.5.
#:
#: Series C discipline passives: ``chastity_discipline`` and ``public_devotion``
#: price at entry (straightforward pray/venue merit modifiers); ``poverty_vow``
#: and ``temple_endurance`` at mid (broad loop multiplier and combat defense
#: penalty mitigation); ``obedience`` at high (doubles offering/climax merit
#: under domination/submission status). Series E utility rites: ``rite_shelter``
#: prices at entry; ``rite_martial_blessing`` and ``rite_morning_devotion`` at
#: mid (morning devotion feeds the prayer loop with +1 daily cap; martial
#: blessing mounts a single-stat buff with clock cooldown). All 8 rows are
#: prereq-free. Daily prayer accrual (40 merit * 3 prayers base = 120 merit/day;
#: 160 with morning devotion), offerings (20..80 copper + row merit), and
#: climax accrual (10 merit) ensure rung 1 (3 skills, ~1150-1550 merit) is
#: reachable in a workday's grind and rung 2 (6 skills) in 2-3 days.
REDEEM_CATALOG: tuple[RedeemRow, ...] = (
    RedeemRow(
        skill_key="pain_to_pleasure",
        merit_price=1800,
        tier="mid",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="priestly_grace",
        merit_price=1500,
        tier="mid",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="rapture_renewal",
        merit_price=2200,
        tier="mid",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="vow_of_service",
        merit_price=500,
        tier="entry",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="rite_heal_light",
        merit_price=400,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_cleanse",
        merit_price=350,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_calm",
        merit_price=450,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_bless_water",
        merit_price=400,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_sanctify_ground",
        merit_price=550,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_absolution",
        merit_price=600,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_lamb_mark",
        merit_price=6000,
        tier="high",
    ),
    RedeemRow(
        skill_key="rite_martyrdom_vow",
        merit_price=6500,
        tier="high",
    ),
    RedeemRow(
        skill_key="rite_anointing_touch",
        merit_price=1400,
        tier="mid",
    ),
    RedeemRow(
        skill_key="rite_milk_blessing",
        merit_price=1800,
        tier="mid",
    ),
    RedeemRow(
        skill_key="rite_holy_kiss",
        merit_price=4000,
        tier="high",
        prereq_keys=("rite_anointing_touch",),
    ),
    RedeemRow(
        skill_key="rite_confession_bed",
        merit_price=8000,
        tier="high",
        prereq_keys=("rite_holy_kiss",),
    ),
    RedeemRow(
        skill_key="poverty_vow",
        merit_price=1500,
        tier="mid",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="obedience",
        merit_price=5000,
        tier="high",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="chastity_discipline",
        merit_price=600,
        tier="entry",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="temple_endurance",
        merit_price=1800,
        tier="mid",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="public_devotion",
        merit_price=500,
        tier="entry",
        polarity="passive",
    ),
    RedeemRow(
        skill_key="rite_martial_blessing",
        merit_price=1600,
        tier="mid",
    ),
    RedeemRow(
        skill_key="rite_shelter",
        merit_price=450,
        tier="entry",
    ),
    RedeemRow(
        skill_key="rite_morning_devotion",
        merit_price=2000,
        tier="mid",
    ),
)

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
