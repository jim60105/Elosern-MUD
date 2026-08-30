"""Small in-memory combat fixtures for pure rules tests."""

from types import SimpleNamespace

from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    lineage_ownership_closure,
    seed_lineage_proficiency,
)
from world.rules.skip_safety import _BATTLEFIELDS


class BattlefieldIsolation:
    """Snapshot and restore the transient skip-safety battlefield registry.

    ``world.rules.skip_safety._BATTLEFIELDS`` is keyed by participant dbrefs,
    which Evennia's test fixtures keep distinct across tests (every ``char1``
    is ``"Char"`` but has its own pk); a combat test that engages without
    settling leaves a stale registration that makes a later skip-safety
    evaluation in the same process report a false "in combat". Every test that
    registers battlefields restores the registry in teardown, and the
    restoration is registered via ``addCleanup`` so a failing ``setUp`` cannot
    leak either.
    """

    def setUp(self):
        super().setUp()
        self.addCleanup(self._restore_battlefields, dict(_BATTLEFIELDS))

    def _restore_battlefields(self, snapshot):
        _BATTLEFIELDS.clear()
        _BATTLEFIELDS.update(snapshot)


class FakeSkills:
    def __init__(self, values: dict[str, int], owned: list[str] | None = None):
        self.values = values
        self._owned = [] if owned is None else owned

    def effective_value(self, key: str) -> int:
        return self.values[key]

    def owned_keys(self) -> list[str]:
        return list(self._owned)

    def conferred_grants(self) -> list:
        return []


class FakeGauge:
    trait_type = "gauge"

    def __init__(self, current: int, maximum: int):
        self._data = {
            "base": maximum,
            "mod": 0,
            "mult": 1,
            "current": current,
        }

    @property
    def value(self) -> int:
        return self._data["current"]

    @value.setter
    def value(self, value: int) -> None:
        self._data["current"] = value

    @property
    def current(self) -> int:
        return self._data["current"]

    @current.setter
    def current(self, value: int) -> None:
        self._data["current"] = value

    @property
    def max(self) -> int:
        return self._data["base"]


def grant_lineage(
    entity,
    active: list[str],
    passive: list[str] | None = None,
    *,
    rungs: dict[str, int] | None = None,
) -> None:
    """Set ``db.skills``/``db.skill_proficiency`` so every listed skill is USABLE.

    The lineage gate (use-driven-skill-lineage) requires prerequisite
    ownership plus threshold proficiency, so a fixture that only lists a deep
    skill is no longer enough. This helper closes the prerequisite-ownership
    chain over ``active`` + ``passive``, seeds the exact minimal prerequisite
    XP via :func:`seed_lineage_proficiency`, and (for freeform fixtures)
    raises the named skills' own proficiency to ``rungs[key]`` levels so the
    skill-anchored ladder unlocks that rung. Existing stored proficiency is
    preserved unless the seed or an explicit rung overwrites it.
    """
    declared_passive = list(passive or [])
    add_active, add_passive = lineage_ownership_closure([*active, *declared_passive])
    skills = {
        "active": [*active, *add_active],
        "passive": [*declared_passive, *add_passive],
    }
    seed = seed_lineage_proficiency(
        [*skills["active"], *skills["passive"]],
        dict(entity.db.skill_proficiency or {}),
    )
    for key, level in (rungs or {}).items():
        seed[key] = max(
            float(seed.get(key, 0.0)), level * SKILL_PROFICIENCY_XP_PER_LEVEL
        )
    entity.db.skills = skills
    entity.db.skill_proficiency = seed


class FakeEntity:
    def __init__(
        self,
        key: str,
        *,
        hp: int = 100,
        max_hp: int | None = None,
        atk_phys: int = 10,
        agility: int = 10,
        defense: int = 5,
        magic_power: int = 10,
        owned: list[str] | None = None,
    ):
        self.key = key
        self.skills = FakeSkills(
            {
                "atk_phys": atk_phys,
                "agility": agility,
                "defense": defense,
                "magic_power": magic_power,
            },
            owned,
        )
        self.traits = SimpleNamespace(hp=FakeGauge(hp, max_hp or hp))
        self.traits.magic_power = FakeGauge(magic_power, magic_power)
        # Minimal buff/equipment storage so the pure combat-modifier query
        # (used by the shared adjusted-stat helpers) evaluates a fake to the
        # empty bundle without materializing any handler.
        self.buffs = SimpleNamespace(all={})
        self.db = SimpleNamespace(equipment=None)
