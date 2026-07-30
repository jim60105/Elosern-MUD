"""Small in-memory combat fixtures for pure rules tests."""

from types import SimpleNamespace


class FakeSkills:
    def __init__(self, values: dict[str, int], owned: list[str] | None = None):
        self.values = values
        self._owned = [] if owned is None else owned

    def effective_value(self, key: str) -> int:
        return self.values[key]

    def owned_keys(self) -> list[str]:
        return list(self._owned)


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
        magic_level: int = 10,
        owned: list[str] | None = None,
    ):
        self.key = key
        self.skills = FakeSkills(
            {
                "atk_phys": atk_phys,
                "agility": agility,
                "defense": defense,
                "magic_level": magic_level,
            },
            owned,
        )
        self.traits = SimpleNamespace(hp=FakeGauge(hp, max_hp or hp))
