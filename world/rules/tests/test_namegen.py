"""Pure-logic tests for the rules-layer name rollers (unittest, no Evennia).

The rollers run on a file-local synthetic name corpus: two bound packs (full
m/f/u given pools plus surnames) and one unbound spare pack, swapped into the
live pack registry and race mapping through the kit's scoped patcher for each
test. A corpus rework (renamed packs, rebound races, replaced vendor data)
therefore cannot break these behavior pins, which exercise the roller's real
mechanics — sex→pool mapping, zh-only composition, bound-pack-only fallback,
KeyError propagation, and the empty-pool fallback.
"""

import inspect
import unittest
from random import Random
from unittest import TestCase
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
import world.rules.namegen as namegen
from world.lore.names import FrozenDict, NAME_SEPARATOR, NamePack, NamePart
from world.rules.namegen import _pick_pack_for_race, _roll_from_pack, roll_name, roll_name_for_race
from world.tests.synthetic_data import synthetic_registries

from ._knowledge_probes import live_name_pack_registry, live_registry

_RANDOM_SEXES = ("", None, "unspecified")


def _part(text: str, zh: str) -> NamePart:
    return NamePart(text=text, zh=zh, meaning_zh="合成語源")


# File-local synthetic corpus. Keys carry the reserved t_ prefix; zh renderings
# are invented and occur nowhere in shipped data; part .text is ASCII and .zh
# never is, preserving the corpus fact the zh-only-composition pin leans on.
_PACK_A_KEY = "t_rillmere_pack"
_PACK_B_KEY = "t_emberfen_pack"
_PACK_SPARE_KEY = "t_sparrowrest_pack"

_PACK_A = NamePack(
    key=_PACK_A_KEY,
    race_key=None,
    surnames=(
        _part("Tarnmere", "澤瀉"),
        _part("Velmara", "葦紋"),
    ),
    given=FrozenDict(
        {
            "m": (_part("Besk", "貝斯克"), _part("Dorran", "多蘭")),
            "f": (_part("Elyra", "艾雷菈"), _part("Nessa", "妮莎")),
            "u": (_part("Uvin", "烏文"),),
        }
    ),
    naming_note_zh="合成語料：bound pack A。",
)
_PACK_B = NamePack(
    key=_PACK_B_KEY,
    race_key=None,
    surnames=(_part("Ondur", "岩響"),),
    given=FrozenDict(
        {
            "m": (_part("Ghairn", "蓋倫"),),
            "f": (_part("Ilyd", "伊呂蒂德"),),
            "u": (_part("Quill", "奎爾"),),
        }
    ),
    naming_note_zh="合成語料：bound pack B。",
)
_PACK_SPARE = NamePack(
    key=_PACK_SPARE_KEY,
    race_key=None,
    surnames=(_part("Korrath", "棘窩"),),
    given=FrozenDict(
        {
            "m": (_part("Helfor", "赫福"),),
            "f": (_part("Missa", "蜜薩"),),
            "u": (_part("Sable", "塞波"),),
        }
    ),
    naming_note_zh="合成語料：未綁定的備用 pack。",
)

# Two synthetic races bind packs; the mapping is complete (bound == all three
# mapping values), and the spare pack stays registry-only — exactly the shipped
# topology's shape with invented identities.
_RACE_A = "t_duskmari"
_RACE_B = "t_mossbrethr"
_SYNTH_RACE_MAP = {_RACE_A: _PACK_A_KEY, _RACE_B: _PACK_B_KEY}
_SYNTH_PACKS = {_PACK_A_KEY: _PACK_A, _PACK_B_KEY: _PACK_B, _PACK_SPARE_KEY: _PACK_SPARE}

# A race key no mapping entry binds — the fallback path's caller.
_UNBOUND_RACE = "t_voidling"


def _live_bound_pack_keys() -> tuple[str, ...]:
    """The CURRENT fallback-candidate tuple, recomputed for the live mapping.

    ``world.rules.namegen`` precomputes its bound-pack tuple at import; inside
    a synthetic scope the mapping carries the synthetic corpus, so behavior
    tests drive the roller against the tuple production WOULD have derived.
    """
    mapping = live_registry("world.lore.names", "NAME_PACK_BY_RACE")
    return tuple(sorted(set(mapping.values())))


def open_name_corpus(test):
    """Enter the synthetic name corpus for one test's full lifecycle."""
    scope = synthetic_registries("name_packs", extra={"name_packs": _SYNTH_PACKS})
    scope.__enter__()
    test.addCleanup(scope.__exit__, None, None, None)
    for target in ("world.lore.names", "world.rules.namegen"):
        patcher = patch(f"{target}.NAME_PACK_BY_RACE", _SYNTH_RACE_MAP)
        patcher.start()
        test.addCleanup(patcher.stop)
    bound = patch(
        "world.rules.namegen._BOUND_PACK_KEYS", _live_bound_pack_keys()
    )
    bound.start()
    test.addCleanup(bound.stop)


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

    def setUp(self):
        open_name_corpus(self)

    @covers_requirement("npc-name-generation::rolling-is-a-pure-function-of-the-injected-rng-for-replayability")
    def test_fixed_seed_replays_identical_names(self):
        calls = [
            (key, sex)
            for key in _SYNTH_PACKS
            for sex in ("female", "male", "other", "", None)
        ] + [
            (race, "female")
            for race in (_RACE_A, _RACE_B, _UNBOUND_RACE, None)
        ]
        for key, sex in calls:
            with self.subTest(key=key, sex=sex):
                first, second = Random(42), Random(42)
                if key in _SYNTH_PACKS:
                    self.assertEqual(
                        roll_name(key, sex, first), roll_name(key, sex, second)
                    )
                else:
                    self.assertEqual(
                        roll_name_for_race(key, sex, first),
                        roll_name_for_race(key, sex, second),
                    )

    @covers_requirement("npc-name-generation::rolling-is-a-pure-function-of-the-injected-rng-for-replayability")
    def test_module_holds_no_rng_state_of_its_own(self):
        source = inspect.getsource(namegen)
        self.assertNotIn("Random()", source)
        for banned in ("random.choice", "random.randint", "random.random", "randrange"):
            self.assertNotIn(banned, source)
        # Every decision flows through the injected instance only; two
        # independent instances of identical seed never influence each other.
        first, second = RecordingRandom(7), RecordingRandom(7)
        sequence_first = [roll_name(_PACK_A_KEY, "", first) for _ in range(5)]
        sequence_second = [roll_name(_PACK_A_KEY, "", second) for _ in range(5)]
        self.assertEqual(sequence_first, sequence_second)
        self.assertTrue(first.choice_calls)
        for call in first.choice_calls:
            self.assertIsInstance(call, tuple)


class RollNameSexPoolTest(TestCase):
    """sex→pool mapping, random-pool normalisation, and output shape."""

    def setUp(self):
        open_name_corpus(self)

    @covers_requirement("npc-name-generation::roll-name-maps-sex-to-the-given-pool-of-a-pack-and-composes-the-chinese-display-name")
    def test_sex_selects_mapped_pool_and_output_is_zh_only(self):
        pack = _PACK_A
        for sex, pool in (("female", "f"), ("male", "m"), ("other", "u")):
            with self.subTest(sex=sex):
                for seed in range(10):
                    name = roll_name(_PACK_A_KEY, sex, Random(seed))
                    given, surname = _segments(name)
                    self.assertIn(given, _pool_zh(pack, pool))
                    self.assertIn(surname, _surname_zh(pack))

    @covers_requirement("npc-name-generation::roll-name-maps-sex-to-the-given-pool-of-a-pack-and-composes-the-chinese-display-name")
    def test_every_pack_output_is_zh_only_for_any_sex(self):
        # Corpus fact behind the contract: part .text is ASCII, .zh never is,
        # so "output contains no ASCII" pins "no text leaks" for every pack.
        for pack_key, pack in _SYNTH_PACKS.items():
            for sex in ("female", "male", "other", "", None):
                with self.subTest(pack=pack_key, sex=sex):
                    name = roll_name(pack_key, sex, Random(11))
                    given, surname = _segments(name)
                    self.assertIn(given, _all_given_zh(pack))
                    self.assertIn(surname, _surname_zh(pack))
                    self.assertFalse(name.isascii())

    @covers_requirement("npc-name-generation::roll-name-maps-sex-to-the-given-pool-of-a-pack-and-composes-the-chinese-display-name")
    def test_unspecified_and_unrecognised_sex_pick_a_random_pool_once(self):
        pack = _PACK_A
        union = _all_given_zh(pack)
        for sex in _RANDOM_SEXES:
            with self.subTest(sex=sex):
                replay_a, replay_b = Random(42), Random(42)
                self.assertEqual(
                    roll_name(_PACK_A_KEY, sex, replay_a),
                    roll_name(_PACK_A_KEY, sex, replay_b),
                )
                recorder = RecordingRandom(3)
                name = roll_name(_PACK_A_KEY, sex, recorder)
                self.assertEqual(recorder.choice_calls[0], ("m", "f", "u"))
                given, surname = _segments(name)
                self.assertIn(given, union)
                self.assertIn(surname, _surname_zh(pack))
        # Unhashable non-str junk joins the unspecified path, never TypeError.
        recorder = RecordingRandom(4)
        name = roll_name(_PACK_A_KEY, [], recorder)
        self.assertEqual(recorder.choice_calls[0], ("m", "f", "u"))
        given, surname = _segments(name)
        self.assertIn(given, union)
        self.assertIn(surname, _surname_zh(pack))


class RollNameForRaceTest(TestCase):
    """Race resolution through the race→pack mapping and the bound-pack fallback."""

    def setUp(self):
        open_name_corpus(self)

    @covers_requirement("npc-name-generation::roll-name-for-race-resolves-via-name-pack-by-race-with-a-bound-packs-only-random-fallback")
    def test_bound_races_roll_from_their_mapped_pack(self):
        mapping = live_registry("world.lore.names", "NAME_PACK_BY_RACE")
        for race, pack_key in mapping.items():
            with self.subTest(race=race):
                pack = live_name_pack_registry()[pack_key]
                for seed in range(5):
                    given, surname = _segments(
                        roll_name_for_race(race, "female", Random(seed))
                    )
                    self.assertIn(given, _all_given_zh(pack))
                    self.assertIn(surname, _surname_zh(pack))

    @covers_requirement("npc-name-generation::roll-name-for-race-resolves-via-name-pack-by-race-with-a-bound-packs-only-random-fallback")
    def test_fallback_candidates_are_exactly_the_sorted_bound_packs(self):
        expected = _live_bound_pack_keys()
        for race_key in (None, _UNBOUND_RACE):
            with self.subTest(race_key=race_key):
                for index, pack_key in enumerate(expected):
                    recorder = RecordingRandom(1, forced_index=index)
                    picked = _pick_pack_for_race(race_key, recorder)
                    self.assertEqual(recorder.choice_calls[-1], expected)
                    self.assertEqual(picked.key, pack_key)

    @covers_requirement("npc-name-generation::roll-name-for-race-resolves-via-name-pack-by-race-with-a-bound-packs-only-random-fallback")
    def test_end_to_end_fallback_never_uses_spare_packs(self):
        bound = set(_live_bound_pack_keys())
        registry = {key: pack for key, pack in live_name_pack_registry().items() if key in _SYNTH_PACKS}
        bound_given = {zh for key in bound for zh in _all_given_zh(registry[key])}
        bound_surnames = {zh for key in bound for zh in _surname_zh(registry[key])}
        spare_only_given = {
            zh
            for key in set(registry) - bound
            for zh in _all_given_zh(registry[key])
        } - bound_given
        spare_only_surnames = {
            zh
            for key in set(registry) - bound
            for zh in _surname_zh(registry[key])
        } - bound_surnames
        self.assertTrue(spare_only_given or spare_only_surnames)
        for race_key in (None, _UNBOUND_RACE):
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

    def setUp(self):
        open_name_corpus(self)

    @covers_requirement("npc-name-generation::unknown-pack-keys-raise-keyerror-and-empty-filtered-pools-fall-back-to-the-full-given-pool")
    def test_unknown_pack_key_propagates_keyerror_verbatim(self):
        missing = "t_unknown_pack"
        self.assertNotIn(missing, live_name_pack_registry())
        with self.assertRaises(KeyError) as caught:
            roll_name(missing, "female", Random(1))
        self.assertEqual(caught.exception.args, (missing,))

    @covers_requirement("npc-name-generation::unknown-pack-keys-raise-keyerror-and-empty-filtered-pools-fall-back-to-the-full-given-pool")
    def test_empty_filtered_pool_falls_back_to_full_given_pool(self):
        part = lambda text, zh: NamePart(text=text, zh=zh, meaning_zh="")  # noqa: E731
        synthetic = NamePack(
            key="t_hollow_pack",
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


if __name__ == "__main__":
    unittest.main()
