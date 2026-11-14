"""The landmark rite completion record: envelope, counts and preservation."""

from __future__ import annotations

import unittest
from copy import deepcopy
from typing import Any, Callable

from world.rules.landmark_rite_record import (
    RECORD_ATTR,
    LandmarkRiteRecordError,
    completed_district_keys,
    empty_record,
    read_record,
    seen_option_keys,
    validate_record,
    with_completion,
    write_record,
)


class _StoredAttributes:
    """The attribute operations the record module uses, in memory."""

    def __init__(self) -> None:
        self.stored: dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.stored.get(key)

    def add(self, key: str, value: Any) -> None:
        self.stored[key] = value


class _Owner:
    """A character with an attribute store and nothing else."""

    def __init__(self) -> None:
        self.attributes = _StoredAttributes()


def _record() -> dict[str, Any]:
    """One valid schema-1 record with an entry and two options."""
    return {
        "schema_version": 1,
        "completed": {
            "t_district": {
                "first_tick": 100,
                "last_tick": 250,
                "count": 2,
                "options": {
                    "t_first": {"count": 1, "last_tick": 100},
                    "t_second": {"count": 1, "last_tick": 250},
                },
            }
        },
    }


def _invalid(label: str, mutate: Callable[[dict[str, Any]], None]) -> tuple[str, Any]:
    record = _record()
    mutate(record)
    return label, record


def _set_district(record: dict[str, Any], entry: Any) -> None:
    record["completed"]["t_district"] = entry


def _set_option(record: dict[str, Any], entry: Any) -> None:
    record["completed"]["t_district"]["options"]["t_first"] = entry


class RecordRoundTripTests(unittest.TestCase):
    def test_a_valid_record_round_trips_through_the_attribute(self):
        owner = _Owner()
        record = _record()
        write_record(owner, record)
        self.assertEqual(read_record(owner), record)
        self.assertEqual(owner.attributes.stored[RECORD_ATTR], record)

    def test_a_missing_attribute_reads_empty_and_creates_nothing(self):
        owner = _Owner()
        self.assertEqual(read_record(owner), empty_record())
        self.assertEqual(owner.attributes.stored, {})
        self.assertEqual(completed_district_keys(owner), frozenset())
        self.assertEqual(seen_option_keys(owner, "t_district"), ())

    def test_completed_districts_and_seen_options_are_the_stored_ones(self):
        owner = _Owner()
        write_record(owner, _record())
        self.assertEqual(completed_district_keys(owner), frozenset({"t_district"}))
        self.assertEqual(
            seen_option_keys(owner, "t_district"), ("t_first", "t_second")
        )
        self.assertEqual(seen_option_keys(owner, "t_elsewhere"), ())

    def test_the_validated_copy_is_independent_of_its_source(self):
        record = _record()
        validated = validate_record(record)
        validated["completed"]["t_district"]["count"] = 9
        self.assertEqual(record["completed"]["t_district"]["count"], 2)


class RecordEnvelopeTests(unittest.TestCase):
    VIOLATIONS = [
        _invalid("extra top-level key", lambda record: record.update({"extra": 1})),
        _invalid(
            "missing top-level key",
            lambda record: record.pop("schema_version"),
        ),
        _invalid(
            "non-mapping record",
            lambda record: record.clear(),
        ),
        _invalid("schema version 2", lambda record: record.update({"schema_version": 2})),
        _invalid(
            "boolean schema version",
            lambda record: record.update({"schema_version": True}),
        ),
        _invalid(
            "completed not a mapping",
            lambda record: record.update({"completed": []}),
        ),
        _invalid(
            "empty district key",
            lambda record: record["completed"].update({"": _record()["completed"]["t_district"]}),
        ),
        _invalid("district entry not a mapping", lambda record: _set_district(record, "x")),
        _invalid(
            "district entry extra key",
            lambda record: _set_district(
                record, {**_record()["completed"]["t_district"], "extra": 1}
            ),
        ),
        _invalid(
            "district count below one",
            lambda record: _set_district(
                record, {**_record()["completed"]["t_district"], "count": 0}
            ),
        ),
        _invalid(
            "district first tick after last tick",
            lambda record: _set_district(
                record,
                {**_record()["completed"]["t_district"], "first_tick": 300},
            ),
        ),
        _invalid(
            "boolean first tick",
            lambda record: _set_district(
                record,
                {**_record()["completed"]["t_district"], "first_tick": True},
            ),
        ),
        _invalid(
            "negative district last tick",
            lambda record: _set_district(
                record,
                {**_record()["completed"]["t_district"], "last_tick": -1},
            ),
        ),
        _invalid(
            "options not a mapping",
            lambda record: _set_district(
                record, {**_record()["completed"]["t_district"], "options": []}
            ),
        ),
        _invalid("option entry not a mapping", lambda record: _set_option(record, 4)),
        _invalid(
            "option entry extra key",
            lambda record: _set_option(record, {"count": 1, "last_tick": 0, "extra": 1}),
        ),
        _invalid(
            "option count below one",
            lambda record: _set_option(record, {"count": 0, "last_tick": 0}),
        ),
        _invalid(
            "negative option last tick",
            lambda record: _set_option(record, {"count": 1, "last_tick": -1}),
        ),
        _invalid(
            "empty option key",
            lambda record: record["completed"]["t_district"]["options"].update(
                {"": {"count": 1, "last_tick": 0}}
            ),
        ),
    ]

    def test_every_envelope_violation_raises(self):
        for label, record in self.VIOLATIONS:
            with self.subTest(label):
                with self.assertRaises(LandmarkRiteRecordError):
                    validate_record(record)

    def test_a_corrupt_stored_value_raises_and_is_left_unchanged(self):
        owner = _Owner()
        corrupt = {"schema_version": 1, "completed": {"t_district": {"count": 0}}}
        owner.attributes.add(RECORD_ATTR, corrupt)
        with self.assertRaises(LandmarkRiteRecordError):
            read_record(owner)
        self.assertEqual(owner.attributes.stored[RECORD_ATTR], corrupt)

    def test_write_record_refuses_an_invalid_record_and_stores_nothing(self):
        owner = _Owner()
        owner.attributes.add(RECORD_ATTR, _record())
        with self.assertRaises(LandmarkRiteRecordError):
            write_record(owner, {"schema_version": 2, "completed": {}})
        self.assertEqual(owner.attributes.stored[RECORD_ATTR], _record())


class RecordCompletionTests(unittest.TestCase):
    def test_the_first_completion_starts_the_district_and_the_option(self):
        updated = with_completion(empty_record(), "t_district", "t_option", 100)
        self.assertEqual(
            updated["completed"]["t_district"],
            {
                "first_tick": 100,
                "last_tick": 100,
                "count": 1,
                "options": {"t_option": {"count": 1, "last_tick": 100}},
            },
        )

    def test_a_repeat_keeps_the_first_tick_and_counts_twice(self):
        once = with_completion(empty_record(), "t_district", "t_option", 100)
        twice = with_completion(once, "t_district", "t_option", 250)
        entry = twice["completed"]["t_district"]
        self.assertEqual(entry["count"], 2)
        self.assertEqual(entry["first_tick"], 100)
        self.assertEqual(entry["last_tick"], 250)
        self.assertEqual(entry["options"]["t_option"], {"count": 2, "last_tick": 250})

    def test_a_second_option_counts_inside_the_same_district(self):
        first = with_completion(empty_record(), "t_district", "t_first", 100)
        repeat = with_completion(first, "t_district", "t_first", 250)
        other = with_completion(repeat, "t_district", "t_second", 300)
        entry = other["completed"]["t_district"]
        self.assertEqual(entry["count"], 3)
        self.assertEqual(entry["first_tick"], 100)
        self.assertEqual(entry["last_tick"], 300)
        self.assertEqual(
            entry["options"],
            {
                "t_first": {"count": 2, "last_tick": 250},
                "t_second": {"count": 1, "last_tick": 300},
            },
        )

    def test_undeclared_district_and_option_entries_survive_a_completion(self):
        stored = {
            "schema_version": 1,
            "completed": {
                "t_retired_district": {
                    "first_tick": 5,
                    "last_tick": 5,
                    "count": 1,
                    "options": {"t_retired_option": {"count": 1, "last_tick": 5}},
                },
                "t_district": {
                    "first_tick": 100,
                    "last_tick": 100,
                    "count": 1,
                    "options": {
                        "t_first": {"count": 1, "last_tick": 100},
                        "t_retired_option": {"count": 3, "last_tick": 90},
                    },
                },
            },
        }
        snapshot = deepcopy(stored)
        updated = with_completion(stored, "t_district", "t_first", 200)
        self.assertEqual(stored, snapshot)
        self.assertEqual(
            updated["completed"]["t_retired_district"],
            snapshot["completed"]["t_retired_district"],
        )
        self.assertEqual(
            updated["completed"]["t_district"]["options"]["t_retired_option"],
            {"count": 3, "last_tick": 90},
        )
        self.assertEqual(
            updated["completed"]["t_district"]["options"]["t_first"],
            {"count": 2, "last_tick": 200},
        )

    def test_a_completion_tick_must_be_a_non_negative_integer(self):
        for tick in (-1, True, None):
            with self.subTest(tick):
                with self.assertRaises(LandmarkRiteRecordError):
                    with_completion(empty_record(), "t_district", "t_option", tick)


if __name__ == "__main__":
    unittest.main()