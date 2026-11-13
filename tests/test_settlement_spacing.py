"""Mechanism tests for the settlement spacing validation.

Every scenario drives synthetic inputs: synthetic places, roads, areas and
thresholds, plus one temporary synthetic workspace for the command. No test
reads the shipped map data, so a placement decision never breaks this module.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

from elosern_map_core.roads_codec import encode_road_document

from tools.settlement_spacing import (
    Area,
    Place,
    SpacingConfig,
    SpacingInput,
    check_spacing,
    load_areas,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_TESTS = REPO_ROOT / "packages" / "map-core" / "tests"
if str(PACKAGE_TESTS) not in sys.path:
    sys.path.insert(0, str(PACKAGE_TESTS))

import authoring_fixtures as fixtures  # noqa: E402

#: A value that is not an authored population, distinct from ``None``.
_UNSET = object()

#: The synthetic region of the shipped fixture continent.
PLAIN = "region_plain"
#: Synthetic thresholds, so no test pins a shipped number.
TIGHT = SpacingConfig(hamlet_min_km=10.0, village_min_km=20.0, road_gap_max_km=4.0)

ROAD = tuple[str, str, tuple[tuple[int, int], ...]]


def _place(
    location_id: str,
    kind: str,
    cell: tuple[int, int] = (0, 0),
    *,
    name: str | None = None,
    exemption: str | None = None,
    nation: str | None = "nation_one",
    population: object = _UNSET,
    has_lore: bool = True,
) -> Place:
    """One synthetic place whose only fault is the one the caller states."""

    if population is _UNSET:
        population = 100 if kind == "hamlet" else 500
    return Place(
        location_id=location_id,
        kind=kind,
        cell=cell,
        display_name_zh=name if name is not None else f"name-{location_id}",
        exemption=exemption,
        nation=nation,
        population=population,  # type: ignore[arg-type]
        has_lore=has_lore,
    )


def _input(
    places: tuple[Place, ...] | list[Place] = (),
    *,
    roads: tuple[ROAD, ...] | list[ROAD] = (),
    areas: tuple[Area, ...] | list[Area] = (),
    region_of=None,
    region_nation: dict[str, str | None] | None = None,
    forbidden: frozenset[str] | set[str] = frozenset(),
) -> SpacingInput:
    """One synthetic input; the default region of every cell carries a nation."""

    return SpacingInput(
        places=tuple(places),
        roads=tuple(roads),
        region_of=region_of if region_of is not None else (lambda cell: PLAIN),
        region_nation=(
            region_nation if region_nation is not None else {PLAIN: "nation_one"}
        ),
        forbidden_regions=frozenset(forbidden),
        areas=tuple(areas),
    )


def _pairs(problems) -> list[tuple[str, str]]:
    return [(problem.code, problem.subject) for problem in problems]


def _straight(first: tuple[int, int], length: int, step: tuple[int, int]) -> tuple:
    """A road of ``length`` cells from ``first`` along ``step``."""

    return tuple(
        (first[0] + step[0] * index, first[1] + step[1] * index)
        for index in range(length)
    )


class MinimumSpacingTests(unittest.TestCase):
    """Minimum spacing is checked by kind in straight-line distance."""

    def test_a_hamlet_at_the_minimum_passes_and_one_cell_closer_fails(self):
        town = _place("town_gate", "town", (0, 0))
        at_limit = _place("hamlet_edge", "hamlet", (0, 10))
        too_close = _place("hamlet_alpha", "hamlet", (0, 9))

        problems = check_spacing(_input([town, at_limit, too_close]), TIGHT)

        # Two pairs are too close and both name the hamlet that stands closer
        # than the minimum to the town: the pair with the town and the pair with
        # the hamlet that sits exactly at the minimum.
        self.assertEqual(
            _pairs(problems),
            [("hamlet_spacing", "hamlet_alpha"), ("hamlet_spacing", "hamlet_alpha")],
        )
        messages = [problem.message for problem in problems]
        self.assertTrue(any("town_gate" in message for message in messages))
        self.assertTrue(any("9.0 km" in message for message in messages))
        self.assertTrue(any("hamlet_edge" in message for message in messages))

    def test_a_village_below_the_minimum_is_reported_and_a_hamlet_pair_is_not(self):
        city = _place("city_big", "city", (0, 0))
        village = _place("village_fair", "village", (0, 19))
        other_village = _place("village_far", "village", (0, 60))
        hamlet = _place("hamlet_mid", "hamlet", (0, 72))
        roads = [
            ("node_fair_a", "node_fair_b", ((0, 19), (1, 19))),
            ("node_far_a", "node_far_b", ((0, 60), (1, 60))),
        ]

        problems = check_spacing(
            _input([city, village, other_village, hamlet], roads=roads), TIGHT
        )

        self.assertEqual(_pairs(problems), [("village_spacing", "village_fair")])
        self.assertIn("city_big", problems[0].message)

    def test_a_hamlet_below_a_village_minimum_is_reported_under_the_hamlet(self):
        # The village comes first in the input, so a subject chosen by "the
        # small kind" rather than by "the hamlet" would report the village.
        village = _place("village_first", "village", (0, 0))
        hamlet = _place("hamlet_later", "hamlet", (0, 5))
        roads = [("node_village_a", "node_village_b", ((0, 0), (1, 0)))]

        problems = check_spacing(_input([village, hamlet], roads=roads), TIGHT)

        self.assertEqual(_pairs(problems), [("hamlet_spacing", "hamlet_later")])
        self.assertIn("village_first", problems[0].message)

    def test_two_villages_too_close_are_reported_once(self):
        alpha = _place("village_alpha", "village", (0, 0))
        beta = _place("village_beta", "village", (0, 10))
        roads = [
            ("node_alpha_a", "node_alpha_b", ((0, 0), (1, 0))),
            ("node_beta_a", "node_beta_b", ((0, 10), (1, 10))),
        ]

        problems = check_spacing(_input([beta, alpha], roads=roads), TIGHT)

        self.assertEqual(_pairs(problems), [("village_spacing", "village_alpha")])
        self.assertIn("village_beta", problems[0].message)

    def test_kinds_that_take_no_part_are_never_reported(self):
        places = [
            _place("hamlet_side", "hamlet", (0, 1)),
            _place("elven_village_hidden", "elven_village", (0, 0), nation=None),
            _place("dungeon_ruin", "dungeon", (1, 1), nation=None),
            _place("town_a", "town", (0, 12)),
            _place("town_b", "town", (0, 13)),
        ]

        self.assertEqual(check_spacing(_input(places), TIGHT), ())

    def test_a_pair_is_reported_once_under_the_smaller_identifier(self):
        first = _place("hamlet_alpha", "hamlet", (0, 0))
        second = _place("hamlet_beta", "hamlet", (0, 5))

        problems = check_spacing(_input([second, first]), TIGHT)

        self.assertEqual(_pairs(problems), [("hamlet_spacing", "hamlet_alpha")])
        self.assertIn("hamlet_beta", problems[0].message)


class ExemptionTests(unittest.TestCase):
    """An exemption mark skips minimum spacing."""

    def test_a_marked_hamlet_is_skipped_by_both_pairs(self):
        town = _place("town_bridge", "town", (0, 0))
        marked = _place(
            "hamlet_garrison",
            "hamlet",
            (0, 9),
            exemption=(
                "Border post beside the bridge town; the garrison lives "
                "outside the walls."
            ),
        )
        unmarked = _place("hamlet_outside", "hamlet", (0, 17))

        self.assertEqual(check_spacing(_input([town, marked, unmarked]), TIGHT), ())

    def test_a_mark_on_another_kind_has_no_effect(self):
        town = _place("town_marked", "town", (0, 0), exemption="A design exception.")
        hamlet = _place("hamlet_plain", "hamlet", (0, 5))

        problems = check_spacing(_input([town, hamlet]), TIGHT)

        self.assertEqual(_pairs(problems), [("hamlet_spacing", "hamlet_plain")])

    def test_a_marked_village_is_skipped_by_both_pairs(self):
        city = _place("city_anchor", "city", (0, 0))
        marked = _place(
            "village_marked",
            "village",
            (0, 19),
            exemption="Design exception; the shrine village belongs to the city.",
        )
        unmarked = _place("village_plain", "village", (0, 30))
        roads = [
            ("node_marked_a", "node_marked_b", ((0, 19), (1, 19))),
            ("node_plain_a", "node_plain_b", ((0, 30), (1, 30))),
        ]

        self.assertEqual(
            check_spacing(_input([city, marked, unmarked], roads=roads), TIGHT), ()
        )


class RoadCoverageTests(unittest.TestCase):
    """Road coverage bounds the gap between consecutive road settlements."""

    def setUp(self):
        self.everywhere = Area("all_plain", PLAIN, None)

    def test_the_gap_boundary_is_inclusive(self):
        roads = [
            ("node_a", "node_b", _straight((0, 0), 5, (1, 0))),
            ("node_a", "node_c", _straight((0, 10), 6, (1, 0))),
        ]

        problems = check_spacing(
            _input(roads=roads, areas=[self.everywhere]), TIGHT
        )

        self.assertEqual(_pairs(problems), [("road_gap", "node_a--node_c")])
        message = problems[0].message
        self.assertIn("(0, 10)", message)
        self.assertIn("(5, 10)", message)
        self.assertIn("5.0 km", message)

    def test_a_hamlet_on_the_road_splits_the_gap(self):
        road = ("node_a", "node_c", _straight((0, 10), 6, (1, 0)))
        hamlet = _place("hamlet_on_road", "hamlet", (2, 10))

        problems = check_spacing(
            _input([hamlet], roads=[road], areas=[self.everywhere]), TIGHT
        )

        self.assertEqual(problems, ())

    def test_a_cell_that_elsewhere_is_a_road_end_counts(self):
        road = ("node_a", "node_c", _straight((0, 10), 6, (1, 0)))
        spur = ("node_d", "node_e", ((2, 11), (2, 10)))

        problems = check_spacing(
            _input(roads=[road, spur], areas=[self.everywhere]), TIGHT
        )

        self.assertEqual(problems, ())

    def test_off_road_places_and_elven_villages_do_not_count(self):
        road = ("node_a", "node_c", _straight((0, 10), 6, (1, 0)))
        beside = _place("hamlet_beside", "hamlet", (2, 11))
        elven = _place("elven_village_on_road", "elven_village", (3, 10), nation=None)

        problems = check_spacing(
            _input([beside, elven], roads=[road], areas=[self.everywhere]), TIGHT
        )

        self.assertEqual(_pairs(problems), [("road_gap", "node_a--node_c")])

    def test_a_diagonal_step_is_the_square_root_of_two(self):
        straight_road = ("node_a", "node_b", _straight((0, 0), 5, (1, 0)))
        diagonal_road = ("node_a", "node_c", _straight((0, 20), 5, (1, 1)))

        diagonal_length = 4 * math.sqrt(2.0)
        self.assertGreater(diagonal_length, TIGHT.road_gap_max_km)
        problems = check_spacing(
            _input(roads=[straight_road, diagonal_road], areas=[self.everywhere]),
            TIGHT,
        )

        self.assertEqual(_pairs(problems), [("road_gap", "node_a--node_c")])


class CompletedAreaTests(unittest.TestCase):
    """Road coverage applies only inside completed areas."""

    def test_inside_a_crossing_and_outside_an_area(self):
        area = Area("west_box", PLAIN, (0, 0, 100, 100))
        roads = [
            ("node_a", "node_b", _straight((10, 0), 16, (1, 0))),
            ("node_a", "node_c", _straight((90, 1), 21, (1, 0))),
            ("node_a", "node_d", _straight((0, 200), 20, (1, 0))),
        ]

        problems = check_spacing(_input(roads=roads, areas=[area]), TIGHT)

        self.assertEqual(_pairs(problems), [("road_gap", "node_a--node_b")])

    def test_a_rectangle_narrows_its_region(self):
        area = Area("narrow", PLAIN, (0, 0, 50, 50))
        road = ("node_a", "node_b", _straight((0, 80), 20, (1, 0)))

        self.assertEqual(
            check_spacing(_input(roads=[road], areas=[area]), TIGHT), ()
        )

    def test_an_empty_area_list_checks_no_gap_but_keeps_the_other_rules(self):
        road = ("node_a", "node_b", _straight((0, 0), 20, (1, 0)))
        town = _place("town_mid", "town", (0, 40))
        hamlet = _place("hamlet_near", "hamlet", (0, 45))

        problems = check_spacing(_input([town, hamlet], roads=[road]), TIGHT)

        self.assertEqual(_pairs(problems), [("hamlet_spacing", "hamlet_near")])


class AreaFileTests(unittest.TestCase):
    """An area file loads cleanly or fails naming the entry that is wrong."""

    def _load(self, document) -> tuple[Area, ...]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "areas.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return load_areas(path)

    def test_a_valid_list_keeps_its_bounds(self):
        areas = self._load(
            {
                "areas": [
                    {"id": "west", "region": PLAIN, "bounds": [0, 0, 4, 4]},
                    {"id": "east", "region": PLAIN},
                ]
            }
        )

        self.assertEqual(
            areas,
            (
                Area("west", PLAIN, (0, 0, 4, 4)),
                Area("east", PLAIN, None),
            ),
        )

    def test_invalid_files_fail_naming_the_entry(self):
        cases = [
            ({"areas": [], "extra": 1}, "extra"),
            ({"areas": {}}, "areas"),
            ({"areas": [{"id": "west", "region": PLAIN, "colour": "red"}]}, "colour"),
            (
                {
                    "areas": [
                        {"id": "west", "region": PLAIN},
                        {"id": "west", "region": PLAIN},
                    ]
                },
                "areas[1]",
            ),
            ({"areas": [{"id": "west", "region": PLAIN, "bounds": [0, 0, 4]}]}, "four"),
            (
                {"areas": [{"id": "west", "region": PLAIN, "bounds": [5, 0, 4, 4]}]},
                "ordered",
            ),
            (
                {
                    "areas": [
                        {"id": "west", "region": PLAIN, "bounds": [0, 0, 4, True]}
                    ]
                },
                "four",
            ),
            ({"areas": [{"id": "  ", "region": PLAIN}]}, "no id"),
            ({"areas": [{"region": PLAIN}]}, "no id"),
            ({"areas": [{"id": "west"}]}, "no region"),
            ({"areas": ["west"]}, "not an object"),
        ]
        for document, expected in cases:
            with self.subTest(document=document):
                with self.assertRaises(ValueError) as captured:
                    self._load(document)
                self.assertIn(expected, str(captured.exception))


class IdentityTests(unittest.TestCase):
    """Villages and hamlets satisfy the placement identity rules."""

    def test_one_fault_each(self):
        def region_of(cell):
            if 210 <= cell[0] < 260:
                return "region_void"
            if cell[0] >= 450:
                return "region_forest"
            return PLAIN

        good_road = ("node_good_a", "node_good_b", ((0, 0), (1, 0)))
        village_roads = [
            ("node_nation_a", "node_nation_b", ((280, 100), (281, 100))),
            ("node_low_a", "node_low_b", ((340, 100), (341, 100))),
            ("node_nopop_a", "node_nopop_b", ((400, 100), (401, 100))),
        ]
        places = [
            _place("village_good", "village", (0, 0)),
            _place("noprefix_place", "hamlet", (100, 100)),
            _place(
                "hamlet_bare",
                "hamlet",
                (160, 100),
                nation=None,
                population=None,
                has_lore=False,
            ),
            _place("hamlet_void", "hamlet", (220, 100)),
            _place("village_wrongnation", "village", (280, 100), nation="nation_two"),
            _place("village_lowpop", "village", (340, 100), population=100),
            _place("village_nopop", "village", (400, 100), population=None),
            _place("hamlet_forbidden", "hamlet", (460, 100)),
            _place("village_offroad", "village", (400, 300)),
        ]

        problems = check_spacing(
            _input(
                places,
                roads=[good_road, *village_roads],
                region_of=region_of,
                region_nation={
                    PLAIN: "nation_one",
                    "region_void": None,
                    "region_forest": "nation_one",
                },
                forbidden={"region_forest"},
            ),
            TIGHT,
        )

        by_subject: dict[str, list[str]] = {}
        for problem in problems:
            by_subject.setdefault(problem.subject, []).append(problem.code)
        self.assertEqual(
            by_subject,
            {
                "noprefix_place": ["id_prefix"],
                "hamlet_bare": ["missing_lore"],
                "hamlet_void": ["no_nation"],
                "village_wrongnation": ["nation_mismatch"],
                "village_lowpop": ["population_range"],
                "village_nopop": ["population_range"],
                "hamlet_forbidden": ["forbidden_region"],
                "village_offroad": ["village_off_road"],
            },
        )
        prefix = next(
            problem for problem in problems if problem.code == "id_prefix"
        )
        self.assertIn("hamlet_", prefix.message)

    def test_a_reserved_prefix_and_a_duplicate_display_name(self):
        places = [
            _place("village_impostor", "town", (0, 0)),
            _place("city_twin", "city", (500, 500), name="同名"),
            _place("hamlet_twin", "hamlet", (900, 900), name="同名"),
        ]

        problems = check_spacing(_input(places), TIGHT)

        self.assertEqual(
            _pairs(problems),
            [("duplicate_name", "city_twin"), ("id_prefix", "village_impostor")],
        )
        self.assertIn("hamlet_twin", problems[0].message)


class CommandTests(unittest.TestCase):
    """The spacing command reports by exit status and writes nothing."""

    def _digests(self, root: Path) -> dict[str, str]:
        return {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def _run(self, arguments: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(arguments)
        return status, out.getvalue(), err.getvalue()

    def _write_workspace(self, root: Path) -> dict[str, str]:
        """A synthetic checkout plus its lore override, roads and area list."""

        continent = fixtures.continent_data()
        for region in continent["regions"].values():
            region["nation_key"] = "nation_one"
        locations = fixtures.locations_data()
        locations["locations"]["hamlet_test"] = {
            "kind": "hamlet",
            "display_name_zh": "測試小村",
            "description": "A synthetic hamlet.",
            "cell": {"cell_x": 5, "cell_y": 25},
            "geographic_constraint": "synthetic",
            "scene_archetype": None,
        }
        for document in fixtures.custom_sources(
            continent=continent,
            locations=locations,
            settlement=fixtures.settlement_data(),
        ):
            path = root / document.relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(document.text, encoding="utf-8")
        (root / "lore.json").write_text(
            json.dumps(
                {
                    "demo_location": {"nation": "nation_one", "population": 1000000},
                    "hamlet_test": {"nation": "nation_one", "population": 120},
                }
            ),
            encoding="utf-8",
        )
        (root / "roads.json").write_text(
            encode_road_document(
                frame_cells=40,
                source_signature="synthetic",
                nodes=["node_a", "node_b"],
                roads=[("node_a", "node_b", ((0, 0), (1, 0)))],
            ),
            encoding="utf-8",
        )
        (root / "areas.json").write_text('{"areas": []}', encoding="utf-8")
        return {
            "--root": str(root),
            "--lore": str(root / "lore.json"),
            "--roads": str(root / "roads.json"),
            "--areas": str(root / "areas.json"),
        }

    def _move_hamlet(self, root: Path, cell_y: int) -> None:
        path = root / fixtures.LOCATIONS_PATH
        parsed = fixtures.parse_document(
            fixtures.LOCATIONS_PATH, path.read_text(encoding="utf-8")
        )
        data = fixtures.plain_data(parsed.document.data)
        data["locations"]["hamlet_test"]["cell"]["cell_y"] = cell_y
        path.write_text(fixtures.yaml_text(data), encoding="utf-8")

    def test_three_runs_report_by_exit_status_and_write_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = self._write_workspace(root)
            argv = [item for pair in arguments.items() for item in pair]

            before = self._digests(root)
            status, out, err = self._run(argv)
            self.assertEqual((status, err), (0, ""))
            self.assertIn("spacing: 0 problems", out)
            self.assertEqual(self._digests(root), before)

            self._move_hamlet(root, 12)
            before = self._digests(root)
            status, out, err = self._run(argv)
            self.assertEqual(status, 1)
            self.assertIn("hamlet_spacing hamlet_test:", out)
            self.assertIn("demo_location", out)
            self.assertIn("spacing: 1 problems", out)
            self.assertEqual(self._digests(root), before)

            (root / "roads.json").write_text('{"version": 1}', encoding="utf-8")
            before = self._digests(root)
            status, out, err = self._run(argv)
            self.assertEqual(status, 2)
            self.assertEqual(out, "")
            self.assertIn("roads.json", err)
            self.assertEqual(self._digests(root), before)

    def test_an_undeclared_area_region_fails_by_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = self._write_workspace(root)
            argv = [item for pair in arguments.items() for item in pair]
            (root / "areas.json").write_text(
                json.dumps({"areas": [{"id": "ghost", "region": "region_nowhere"}]}),
                encoding="utf-8",
            )

            status, out, err = self._run(argv)

            self.assertEqual((status, out), (2, ""))
            self.assertIn("ghost", err)
            self.assertIn("region_nowhere", err)


if __name__ == "__main__":
    unittest.main()