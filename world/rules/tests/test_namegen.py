"""Pure-logic tests for the rules-layer name rollers (unittest, no Evennia).

Traceability annotations are deferred to the archive-sync stage: the
`npc-name-generation` delta IDs are not in the main index yet, and early
`@covers_requirement` claims are unknown-requirement-id errors (precedent
`npc-namegen-lore-registry` task 4.1).
"""

import inspect
from random import Random
from unittest import TestCase

import world.rules.namegen as namegen
from world.lore.names import (
    NAME_PACK_BY_RACE,
    NAME_PACK_REGISTRY,
    NAME_SEPARATOR,
    NamePack,
    NamePart,
)
from world.rules.namegen import _BOUND_PACK_KEYS, _pick_pack_for_race, _roll_from_pack, roll_name, roll_name_for_race


_PACK_KEYS = tuple(NAME_PACK_REGISTRY)
_RANDOM_SEXES = ("", None, "unspecified")


class RecordingRandom(Random):
    """Random that records every ``choice`` candidate sequence and can force an index."""

    def __init__(self, seed=None, forced_index=None):
        super().__init__(seed)
        self.choice_calls: list[tuple] = []
        self.forced_index = forced_index

    def choice(self, seq):
        self.choice_calls.append(tuple(seq))
        if self.forced_index is not None:
            return seq[self.forced_index % len(seq)]
        return super().choice(seq)


def _pool_zh(pack: NamePack, pool: str) -> set[str]:
    return {part.zh for part in pack.given[pool]}


def _all_given_zh(pack: NamePack) -> set[str]:
    return {part.zh for pool in ("m", "f", "u") for part in pack.given[pool]}


def _surname_zh(pack: NamePack) -> set[str]:
    return {part.zh for part in pack.surnames}


def _segments(name: str) -> tuple[str, str]:
    given, _, surname = name.partition(NAME_SEPARATOR)
    return given, surname


class RollNameReplayTest(TestCase):
    """Fixed-seed determinism and the no-global-RNG contract."""


    def test_fixed_seed_replays_identical_names(self):
        calls = [
            (key, sex)
            for key in _PACK_KEYS
            for sex in ("female", "male", "other", "", None)
        ] + [
            (race, "female") for race in ("human", "elf", "beastfolk", None, "dragonborn")
        ]
        for key, sex in calls:
            with self.subTest(key=key, sex=sex):
                first, second = Random(42), Random(42)
                if key in NAME_PACK_REGISTRY:
                    self.assertEqual(
                        roll_name(key, sex, first), roll_name(key, sex, second)
                    )
                else:
                    self.assertEqual(
                        roll_name_for_race(key, sex, first),
                        roll_name_for_race(key, sex, second),
                    )


    def test_module_holds_no_rng_state_of_its_own(self):
        source = inspect.getsource(namegen)
        self.assertNotIn("Random()", source)
        for banned in ("random.choice", "random.randint", "random.random", "randrange"):
            self.assertNotIn(banned, source)
        # Every decision flows through the injected instance only; two
        # independent instances of identical seed never influence each other.
        first, second = RecordingRandom(7), RecordingRandom(7)
        sequence_first = [roll_name("fantasy-elf", "", first) for _ in range(5)]
        sequence_second = [roll_name("fantasy-elf", "", second) for _ in range(5)]
        self.assertEqual(sequence_first, sequence_second)
        self.assertTrue(first.choice_calls)
        for call in first.choice_calls:
            self.assertIsInstance(call, tuple)


class RollNameSexPoolTest(TestCase):
    """sex→pool mapping, random-pool normalisation, and output shape."""

    def test_sex_selects_mapped_pool_and_output_is_zh_only(self):
        pack = NAME_PACK_REGISTRY["fantasy-human"]
        for sex, pool in (("female", "f"), ("male", "m"), ("other", "u")):
            with self.subTest(sex=sex):
                for seed in range(10):
                    name = roll_name("fantasy-human", sex, Random(seed))
                    given, surname = _segments(name)
                    self.assertIn(given, _pool_zh(pack, pool))
                    self.assertIn(surname, _surname_zh(pack))

    def test_every_pack_output_is_zh_only_for_any_sex(self):
        # Corpus fact behind the contract: part .text is ASCII, .zh never is,
        # so "output contains no ASCII" pins "no text leaks" for every pack.
        for pack_key in _PACK_KEYS:
            pack = NAME_PACK_REGISTRY[pack_key]
            for sex in ("female", "male", "other", "", None):
                with self.subTest(pack=pack_key, sex=sex):
                    name = roll_name(pack_key, sex, Random(11))
                    given, surname = _segments(name)
                    self.assertIn(given, _all_given_zh(pack))
                    self.assertIn(surname, _surname_zh(pack))
                    self.assertFalse(name.isascii())

    def test_unspecified_and_unrecognised_sex_pick_a_random_pool_once(self):
        pack = NAME_PACK_REGISTRY["fantasy-human"]
        union = _all_given_zh(pack)
        for sex in _RANDOM_SEXES:
            with self.subTest(sex=sex):
                replay_a, replay_b = Random(42), Random(42)
                self.assertEqual(
                    roll_name("fantasy-human", sex, replay_a),
                    roll_name("fantasy-human", sex, replay_b),
                )
                recorder = RecordingRandom(3)
                name = roll_name("fantasy-human", sex, recorder)
                self.assertEqual(recorder.choice_calls[0], ("m", "f", "u"))
                given, surname = _segments(name)
                self.assertIn(given, union)
                self.assertIn(surname, _surname_zh(pack))
        # Unhashable non-str junk joins the unspecified path, never TypeError.
        recorder = RecordingRandom(4)
        name = roll_name("fantasy-human", [], recorder)
        self.assertEqual(recorder.choice_calls[0], ("m", "f", "u"))
        given, surname = _segments(name)
        self.assertIn(given, union)
        self.assertIn(surname, _surname_zh(pack))


class RollNameForRaceTest(TestCase):
    """Race resolution through NAME_PACK_BY_RACE and the bound-pack fallback."""


    def test_bound_races_roll_from_their_mapped_pack(self):
        for race, pack_key in NAME_PACK_BY_RACE.items():
            with self.subTest(race=race):
                pack = NAME_PACK_REGISTRY[pack_key]
                for seed in range(5):
                    given, surname = _segments(
                        roll_name_for_race(race, "female", Random(seed))
                    )
                    self.assertIn(given, _all_given_zh(pack))
                    self.assertIn(surname, _surname_zh(pack))


    def test_fallback_candidates_are_exactly_the_sorted_bound_packs(self):
        expected = tuple(sorted(set(NAME_PACK_BY_RACE.values())))
        self.assertEqual(_BOUND_PACK_KEYS, expected)
        for race_key in (None, "dragonborn"):
            with self.subTest(race_key=race_key):
                for index, pack_key in enumerate(expected):
                    recorder = RecordingRandom(1, forced_index=index)
                    picked = _pick_pack_for_race(race_key, recorder)
                    self.assertEqual(recorder.choice_calls[-1], expected)
                    self.assertEqual(picked.key, pack_key)


    def test_end_to_end_fallback_never_uses_spare_packs(self):
        bound = set(_BOUND_PACK_KEYS)
        bound_given = {
            zh for key in bound for zh in _all_given_zh(NAME_PACK_REGISTRY[key])
        }
        bound_surnames = {
            zh for key in bound for zh in _surname_zh(NAME_PACK_REGISTRY[key])
        }
        spare_only_given = {
            zh
            for key in set(_PACK_KEYS) - bound
            for zh in _all_given_zh(NAME_PACK_REGISTRY[key])
        } - bound_given
        spare_only_surnames = {
            zh
            for key in set(_PACK_KEYS) - bound
            for zh in _surname_zh(NAME_PACK_REGISTRY[key])
        } - bound_surnames
        self.assertTrue(spare_only_given or spare_only_surnames)
        for race_key in (None, "dragonborn"):
            for seed in range(60):
                given, surname = _segments(
                    roll_name_for_race(race_key, "other", Random(seed))
                )
                self.assertIn(given, bound_given)
                self.assertIn(surname, bound_surnames)
                self.assertNotIn(given, spare_only_given)
                self.assertNotIn(surname, spare_only_surnames)


class ErrorSemanticsTest(TestCase):
    """KeyError propagation and the empty-pool full-given fallback."""


    def test_unknown_pack_key_propagates_keyerror_verbatim(self):
        with self.assertRaises(KeyError) as caught:
            roll_name("fantasy-dragonkin", "female", Random(1))
        self.assertEqual(caught.exception.args, ("fantasy-dragonkin",))


    def test_empty_filtered_pool_falls_back_to_full_given_pool(self):
        part = lambda text, zh: NamePart(text=text, zh=zh, meaning_zh="")  # noqa: E731
        synthetic = NamePack(
            key="synthetic",
            race_key=None,
            surnames=(part("Grim", "grim-zh"),),
            given={"m": (part("Bron", "bron-zh"),), "f": (part("Ada", "ada-zh"),), "u": ()},
            naming_note_zh="synthetic note",
        )
        for seed in range(10):
            given, surname = _segments(_roll_from_pack(synthetic, "other", Random(seed)))
            self.assertIn(given, {"bron-zh", "ada-zh"})
            self.assertEqual(surname, "grim-zh")
        # The normal path on the same pack is untouched.
        given, _ = _segments(_roll_from_pack(synthetic, "female", Random(2)))
        self.assertEqual(given, "ada-zh")
