"""Data-contract test: authored room prose language contract
The guard the grid-room-sync authored-room-prose requirement demands: every
authored room description the game ships — grid prototype ``desc`` values and
place interior descriptions — is Traditional Chinese prose, and every room's
name and description are in the same language. The check runs over the shipped
registries through the shared heuristic in ``world.lore.settlements._prose_lang``
so a new English description fails the suite rather than accumulating; nothing
here pins a particular sentence."""

from tools.spec_traceability import covers_requirement

import re
import unittest

from world.lore.settlements._prose_lang import english_prose_defects
from world.lore.settlements.places import PLACE_REGISTRY
from world.maps.altoria_capital import PROTOTYPES as CAPITAL_PROTOTYPES
from world.maps.limbo import LIMBO_DESC, LIMBO_KEY
from world.maps.village_ciaran import PROTOTYPES as VILLAGE_PROTOTYPES


def _is_han(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff"


def _shipped_authored_rooms():
    """(label, name, description) for every authored room description shipped."""
    for place in PLACE_REGISTRY.values():
        yield place.key, place.room_name_zh, place.room_desc_zh
    for map_name, prototypes in (
        ("capital_altoria", CAPITAL_PROTOTYPES),
        ("village_ciaran", VILLAGE_PROTOTYPES),
    ):
        for coordinate, prototype in prototypes.items():
            desc = prototype.get("desc")
            if desc:
                yield (
                    f"{map_name}{coordinate}",
                    prototype.get("key", ""),
                    desc,
                )
    yield "limbo", LIMBO_KEY, LIMBO_DESC


class AuthoredRoomProseLanguageTests(unittest.TestCase):
    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_every_shipped_room_description_is_traditional_chinese(self):
        corpus = list(_shipped_authored_rooms())
        # Guard sanity: the corpus actually covers both description kinds.
        self.assertEqual(len(corpus), len(PLACE_REGISTRY) + 32, "corpus regressed")
        for label, _name, desc in corpus:
            with self.subTest(room=label):
                self.assertEqual(english_prose_defects(label, desc), [])

    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_room_name_and_description_agree_in_language(self):
        for label, name, desc in _shipped_authored_rooms():
            with self.subTest(room=label):
                name_is_han = any(_is_han(char) for char in name)
                desc_is_han = any(_is_han(char) for char in desc)
                self.assertEqual(
                    name_is_han,
                    desc_is_han,
                    f"{label}: room name and description are in different languages",
                )

    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_no_shipped_description_carries_an_authoring_note(self):
        # A kebab-case latin identifier is a spec/change name (or a design
        # decision id) that leaked into player-facing text; the shipped prose
        # carries zero of them, so the check is a general rule, not a list.
        identifier = re.compile(r"[A-Za-z]+(?:-[A-Za-z0-9]+)+")
        for label, _name, desc in _shipped_authored_rooms():
            with self.subTest(room=label):
                self.assertNotIn("§", desc)
                self.assertIsNone(
                    identifier.search(desc),
                    f"{label}: description carries a spec/change identifier",
                )

    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_authoring_note_fails_the_check(self):
        # A Chinese description whose Han majority is untouched, but which
        # names the change that wrote it — the authoring-note defect the
        # scenario forbids, in the exact form the substring list would miss.
        identifier = re.compile(r"[A-Za-z]+(?:-[A-Za-z0-9]+)+")
        self.assertIsNotNone(
            identifier.search("這間屋子是在 altoria-capital-replan 之後重寫的。"),
            "a spec/change identifier passed the authoring-note check",
        )

    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_synthetic_english_description_fails_the_guard(self):
        defects = english_prose_defects(
            "合成房間",
            "This is a fully English description of a room in the game world.",
        )
        self.assertTrue(defects, "an English description passed the guard")
        self.assertTrue(any("合成房間" in defect for defect in defects))

    @covers_requirement(
        "grid-room-sync::authored-room-prose-is-traditional-chinese"
    )
    def test_mixed_room_with_english_body_fails_the_guard(self):
        # The exact shipped defect: a Chinese room name over an English body.
        defects = english_prose_defects(
            "爐火旅店",
            "旅店的門後各是一張床。The quiet hours here are for resting.",
        )
        self.assertTrue(defects, "an English body under a Chinese name passed")


if __name__ == "__main__":
    unittest.main()
