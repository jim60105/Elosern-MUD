"""Map-district document loading and validation over synthetic fixtures.

The documents, terrain, settlement bindings and regions here are file-local
synthetic fixtures: a 400 by 400 frame whose western strip is sea, a blocked
wall column, a northern ``fen`` region, an unreachable eastern island and one
synthetic settlement. Structural faults reject the candidate; terrain and
spacing findings stay loadable as saveable work in progress and reject runtime
adoption. Shipped content is covered by ``test_map_district_content``.
"""

import hashlib
import json
import unittest
from unittest import mock

from elosern_map_core.authoring import AuthoringError
from elosern_map_core.diagnostics import SEMANTIC, STRUCTURE
from elosern_map_core.documents import DistrictDeclaration
from elosern_map_core.references import (
    ReferenceIndex,
    interior_room_ref,
    settlement_node_ref,
    wilderness_cell_ref,
)
from tools.spec_traceability import covers_requirement
from world.lore import map_districts
from world.maps import runtime
from world.lore.map_districts import (
    DISTRICTS_PATH,
    MIN_VORONOI_SPACING_KM,
    DistrictError,
    DistrictNotLoaded,
    GridSite,
    build_districts,
    cell_of_position,
    diagnose_districts,
    landmark_node_ids,
    parse_districts_document,
)
from world.tests.geography_fixture import (
    publish_districts,
    publish_shipped_geography,
)


def setUpModule():
    # Encoding a canonical visit id validates its cell against the published
    # frame; the mechanism fixtures stay synthetic.
    publish_shipped_geography()

_WALL_X = 200
_FEN_Y = 300


class _Terrain:
    wilderness_name = "testland"
    max_cell = (399, 399)
    region_keys = frozenset({"plain", "fen"})

    #: Settlement nodes: (map, xy) -> site. The second is cut off from every
    #: gateway; the third sits in the western sea.
    grid_sites = {
        ("testtown", (40, 60)): GridSite(position_m=(150_200, 150_700), reachable=True),
        ("testtown", (41, 60)): GridSite(position_m=(151_000, 150_700), reachable=False),
        ("testtown", (42, 60)): GridSite(position_m=(4_000, 150_700), reachable=True),
    }

    def is_land(self, cell):
        return cell[0] >= 10

    def is_walkable(self, cell):
        return self.is_land(cell) and not (cell[0] == _WALL_X and cell[1] < _FEN_Y)

    def is_reachable(self, cell):
        return self.is_walkable(cell) and cell[0] < 380

    def region_of(self, cell):
        return "fen" if cell[1] >= _FEN_Y else "plain"

    def grid_site(self, map_key, xy):
        return self.grid_sites.get((map_key, tuple(xy)))


#: The settlement-node bindings the synthetic districts resolve against.
_INDEX = ReferenceIndex.build(
    settlement_nodes=[
        ("testtown", "town_node", (40, 60)),
        ("testtown", "cut_node", (41, 60)),
        ("testtown", "dock_node", (42, 60)),
        ("testtown", "moved_node", (40, 60)),
    ],
    interior_rooms=[("testtown", "inner")],
    frame_cells=400,
)


def _cell(x, y):
    return {"domain": "wilderness_cell", "map_id": None, "object_id": None,
            "cell": {"cell_x": x, "cell_y": y}}


def _node(map_id, object_id):
    return {"domain": "settlement_node", "map_id": map_id, "object_id": object_id,
            "cell": None}


def _room(map_id, object_id):
    return {"domain": "interior_room", "map_id": map_id, "object_id": object_id,
            "cell": None}


def _row(name, landmark_name, landmark, kind="voronoi", region_key=None):
    return {
        "district_name_zh": name,
        "landmark_name_zh": landmark_name,
        "landmark": landmark,
        "kind": kind,
        "region_key": region_key,
    }


def _document(rows):
    """Parse one synthetic district document through the real codec."""

    data = {
        "version": 1,
        "kind": "districts",
        "id": "districts",
        "districts": rows,
    }
    return parse_districts_document(json.dumps(data, ensure_ascii=False))


def _valid_rows():
    return {
        "fen_heart": _row(
            "合成沼心區", "合成沼心碑", _cell(250, 350), "region", "fen"
        ),
        "west_seed": _row("合成西區", "合成西碑", _cell(50, 50)),
        "east_seed": _row("合成東區", "合成東碑", _cell(300, 50)),
        "town_seed": _row("合成城區", "合成城碑", _node("testtown", "town_node")),
    }


def _build(rows, *, terrain=None, index=_INDEX):
    return build_districts(
        _document(rows),
        terrain=terrain or _Terrain(),
        index=index,
    )


def _diagnose(rows, *, terrain=None, index=_INDEX):
    return diagnose_districts(
        _document(rows).districts,
        terrain=terrain or _Terrain(),
        index=index,
    )


def _by_object(diagnostics):
    found = {}
    for item in diagnostics:
        found.setdefault(item.object_id, []).append(item)
    return found


class DistrictDocumentTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_a_valid_document_loads_without_diagnostics(self):
        rows = _valid_rows()
        self.assertEqual(_diagnose(rows), ())
        snapshot = _build(rows)
        self.assertEqual(tuple(snapshot.districts), tuple(rows))
        self.assertEqual(snapshot.diagnostics, ())
        # The parsed document is the single source: the snapshot carries its
        # relative path and content fingerprint, so a name-only edit changes
        # the published identity without touching any landmark reference.
        self.assertEqual(snapshot.document.relative_path, DISTRICTS_PATH)
        self.assertEqual(
            dict(snapshot.fingerprints),
            {DISTRICTS_PATH: snapshot.document.fingerprint},
        )
        expected = hashlib.sha256(
            (DISTRICTS_PATH + "\0" + snapshot.document.fingerprint + "\0").encode(
                "utf-8"
            )
        ).hexdigest()
        self.assertEqual(snapshot.identity, expected)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_publish_adopts_a_clean_candidate_and_rejects_a_diagnosed_one(self):
        saved = runtime.current()
        clean = _build(_valid_rows())
        try:
            self.assertIs(publish_districts(clean), clean)
            self.assertIs(map_districts.current(), clean)
            self.assertTrue(map_districts.is_published())

            # A terrain semantic fault loads (saveable work in progress) but
            # never replaces the published baseline.
            broken_rows = _valid_rows() | {
                "sea_seed": _row("合成海區", "合成海碑", _cell(5, 150))
            }
            candidate = _build(broken_rows)
            self.assertEqual(
                [item.code for item in candidate.diagnostics], ["landmark_in_sea"]
            )
            with self.assertRaises(DistrictError) as caught:
                publish_districts(candidate)
            self.assertEqual(
                [item.code for item in caught.exception.diagnostics],
                ["landmark_in_sea"],
            )
            self.assertIs(map_districts.current(), clean)
        finally:
            publish_districts(saved.districts)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_name_edit_keeps_identity_and_reaches_consumers(self):
        rows = _valid_rows()
        original = _build(rows)
        edited_rows = dict(rows)
        edited_rows["west_seed"] = _row("合成西區改名", "合成西碑改名", _cell(50, 50))
        edited = _build(edited_rows)
        self.assertEqual(tuple(original.districts), tuple(edited.districts))
        self.assertEqual(
            original.districts["west_seed"].landmark,
            edited.districts["west_seed"].landmark,
        )
        self.assertEqual(
            landmark_node_ids(original.districts, index=_INDEX),
            landmark_node_ids(edited.districts, index=_INDEX),
        )
        self.assertNotEqual(original.identity, edited.identity)
        saved = runtime.current()
        try:
            publish_districts(edited)
            district = map_districts.current().districts["west_seed"]
            self.assertEqual(district.district_name_zh, "合成西區改名")
            self.assertEqual(district.landmark_name_zh, "合成西碑改名")
        finally:
            publish_districts(saved.districts)


class DistrictStructureTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_unknown_reference_interior_room_and_region_are_structural(self):
        rows = _valid_rows() | {
            "ghost_seed": _row("合成幽區", "合成幽碑", _node("testtown", "ghost_node")),
            "room_seed": _row("合成室區", "合成室碑", _room("testtown", "inner")),
            "bad_region": _row("合成異區", "合成異碑", _cell(250, 150), "region", "moor"),
        }
        diagnostics = _diagnose(rows)
        self.assertEqual({item.category for item in diagnostics}, {STRUCTURE})
        found = _by_object(diagnostics)
        self.assertEqual(found["ghost_seed"][0].code, "unknown_reference")
        self.assertIn("no authored node", found["ghost_seed"][0].message)
        self.assertEqual(found["room_seed"][0].code, "unsupported_landmark_domain")
        self.assertEqual(found["bad_region"][0].code, "unknown_region")
        with self.assertRaises(DistrictError) as caught:
            _build(rows)
        self.assertEqual(
            {item.object_id for item in caught.exception.diagnostics},
            {"ghost_seed", "room_seed", "bad_region"},
        )

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_duplicate_identities_and_misfiled_rows_are_structural(self):
        rows = _valid_rows() | {
            "twin_node": _row("合成雙區", "合成雙碑", _cell(50, 50)),
            "twin_names": _row("合成西區", "合成西碑", _cell(150, 150)),
            "fen_rim": _row("合成沼緣區", "合成沼緣碑", _cell(100, 390), "region", "fen"),
        }
        found = _by_object(_diagnose(rows))
        self.assertIn("duplicate_landmark", [item.code for item in found["twin_node"]])
        self.assertIn(
            "duplicate_district_name_zh", [item.code for item in found["twin_names"]]
        )
        self.assertIn(
            "duplicate_landmark_name_zh", [item.code for item in found["twin_names"]]
        )
        self.assertIn("duplicate_region_key", [item.code for item in found["fen_rim"]])

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_unreachable_frame_and_misfiled_bindings_are_reported(self):
        rows = _valid_rows() | {
            "sea_seed": _row("合成海區", "合成海碑", _cell(5, 150)),
            "wall_seed": _row("合成牆區", "合成牆碑", _cell(_WALL_X, 150)),
            "island_seed": _row("合成島區", "合成島碑", _cell(390, 150)),
            "cut_seed": _row("合成斷區", "合成斷碑", _node("testtown", "cut_node")),
            "dock_seed": _row("合成港區", "合成港碑", _node("testtown", "dock_node")),
            "beyond_seed": _row("合成外區", "合成外碑", _cell(400, 50)),
        }
        found = _by_object(_diagnose(rows))
        self.assertEqual(found["sea_seed"][0].code, "landmark_in_sea")
        self.assertEqual(found["wall_seed"][0].code, "landmark_blocked")
        self.assertEqual(found["island_seed"][0].code, "unreachable_landmark")
        self.assertEqual(found["cut_seed"][0].code, "unreachable_landmark")
        self.assertEqual(found["dock_seed"][0].code, "landmark_in_sea")
        self.assertEqual(found["beyond_seed"][0].code, "invalid_reference")
        self.assertEqual(found["beyond_seed"][0].category, STRUCTURE)
        for key in ("sea_seed", "wall_seed", "island_seed", "cut_seed", "dock_seed"):
            self.assertEqual(found[key][0].category, SEMANTIC, key)

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_a_resolved_grid_landmark_without_a_binding_is_unbound(self):
        # The authored node exists in the binding index but this world has no
        # continental projection for it yet: saveable work, not a bad identity.
        terrain = _Terrain()
        rows = _valid_rows() | {
            "pending_seed": _row("合成待區", "合成待碑", _node("othertown", "plaza"))
        }
        index = ReferenceIndex.build(
            settlement_nodes=[("othertown", "plaza", (10, 10))], frame_cells=400
        )
        found = _by_object(_diagnose(rows, terrain=terrain, index=index))
        self.assertEqual(found["pending_seed"][0].code, "unbound_landmark")
        self.assertEqual(found["pending_seed"][0].category, SEMANTIC)

    def test_programmatic_declarations_still_face_the_identity_rules(self):
        # Schema rules guarantee kind/region pairing for parsed documents; a
        # programmatic candidate is still checked, never trusted.
        declaration = DistrictDeclaration(
            district_id="loose_region",
            district_name_zh="合成鬆區",
            landmark_name_zh="合成鬆碑",
            landmark=wilderness_cell_ref((50, 150)),
            kind="voronoi",
            region_key="plain",
        )
        diagnostics = diagnose_districts(
            {"loose_region": declaration}, terrain=_Terrain(), index=_INDEX
        )
        self.assertEqual(
            [item.code for item in diagnostics], ["invalid_region_membership"]
        )


class DistrictSpacingAndMembershipTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_voronoi_spacing_is_the_single_declared_minimum(self):
        self.assertEqual(MIN_VORONOI_SPACING_KM, 100)
        # Cell centres 100 cells apart are exactly 100 km apart: allowed.
        self.assertEqual(
            _diagnose(
                {
                    "near_a": _row("合成甲區", "合成甲碑", _cell(50, 50)),
                    "near_b": _row("合成乙區", "合成乙碑", _cell(150, 50)),
                }
            ),
            (),
        )
        # 99 cells apart is below the minimum, and the pair is named.
        diagnostics = _diagnose(
            {
                "near_a": _row("合成甲區", "合成甲碑", _cell(50, 50)),
                "near_b": _row("合成乙區", "合成乙碑", _cell(149, 50)),
            }
        )
        self.assertEqual([item.code for item in diagnostics], ["invalid_spacing"])
        self.assertEqual(
            diagnostics[0].message,
            "landmark is 99.0 km from 'near_b', below the 100 km minimum spacing",
        )
        self.assertEqual(diagnostics[0].category, SEMANTIC)
        # A grid landmark is measured at its continental position: the town
        # node at (150.2 km, 150.7 km) is 0.36 km from the centre of cell (150, 150).
        diagnostics = _diagnose(
            {
                "town_seed": _row("合成城區", "合成城碑", _node("testtown", "town_node")),
                "by_town": _row("合成鄰區", "合成鄰碑", _cell(150, 150)),
            }
        )
        self.assertEqual(
            [item.message for item in diagnostics],
            ["landmark is 0.4 km from 'by_town', below the 100 km minimum spacing"],
        )
        # Region districts are exempt: the forest heart may sit next to a seed.
        self.assertEqual(
            _diagnose(
                {
                    "fen_heart": _row(
                        "合成沼心區", "合成沼心碑", _cell(150, 300), "region", "fen"
                    ),
                    "by_fen": _row("合成臨區", "合成臨碑", _cell(150, 299)),
                }
            ),
            (),
        )

    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_region_membership_governs_both_kinds(self):
        found = _by_object(
            _diagnose(
                {
                    "fen_heart": _row(
                        "合成沼心區", "合成沼心碑", _cell(150, 150), "region", "fen"
                    ),
                    "fen_seed": _row("合成沼邊區", "合成沼邊碑", _cell(50, 350)),
                }
            )
        )
        self.assertEqual(found["fen_heart"][0].code, "region_mismatch")
        self.assertIn("not 'fen'", found["fen_heart"][0].message)
        self.assertEqual(found["fen_seed"][0].code, "region_territory_overlap")
        self.assertEqual(found["fen_seed"][0].category, SEMANTIC)


class DistrictSourceBoundaryTests(unittest.TestCase):
    def test_duplicate_yaml_keys_are_rejected_by_the_codec(self):
        data = {
            "version": 1,
            "kind": "districts",
            "id": "districts",
            "districts": {
                "west_seed": _row("合成西區", "合成西碑", _cell(50, 50)),
            },
        }
        text = json.dumps(data, ensure_ascii=False).replace(
            '"west_seed":',
            '"west_seed": {},\n    "west_seed":',
            1,
        )
        with self.assertRaises(AuthoringError):
            parse_districts_document(text)

    def test_invalid_kind_and_region_shape_are_structural_at_parse(self):
        for row in (
            _row("odd_kind", "合成方碑", _cell(50, 50), "square"),
            _row("no_region", "合成無碑", _cell(250, 50), "region"),
        ):
            with self.subTest(district=next(iter(row))):
                with self.assertRaises(AuthoringError) as caught:
                    _document({next(iter(row)): row})
                self.assertTrue(caught.exception.diagnostics)

    def test_a_missing_source_rejects_without_touching_the_baseline(self):
        import tempfile

        from pathlib import Path

        saved = runtime.current()
        clean = _build(_valid_rows())
        try:
            publish_districts(clean)
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(runtime.MapWorldError) as caught:
                    runtime.adopt(Path(directory))
            self.assertIn("the required districts document is absent", str(caught.exception))
            self.assertIs(map_districts.current(), clean)
        finally:
            publish_districts(saved.districts)


class LandmarkIdentityTests(unittest.TestCase):
    @covers_requirement(
        "map-districts::every-map-district-has-one-canonical-reachable-landmark"
    )
    def test_a_settlement_landmark_follows_its_moved_node_by_stable_identity(self):
        rows = {
            "town_seed": _row("合成城區", "合成城碑", _node("testtown", "moved_node"))
        }
        document = _document(rows)
        district = document.districts["town_seed"]
        # No coordinate is authored for the landmark: only the qualified id.
        self.assertEqual(district.landmark, settlement_node_ref("testtown", "moved_node"))
        self.assertIsNone(district.landmark.cell)

        before = landmark_node_ids(
            document.districts,
            index=ReferenceIndex.build(
                settlement_nodes=[("testtown", "moved_node", (10, 10))],
                frame_cells=400,
            ),
        )
        after = landmark_node_ids(
            document.districts,
            index=ReferenceIndex.build(
                settlement_nodes=[("testtown", "moved_node", (40, 40))],
                frame_cells=400,
            ),
        )
        self.assertEqual(before, {"town_seed": "grid:testtown:10:10"})
        self.assertEqual(after, {"town_seed": "grid:testtown:40:40"})

    def test_cell_of_position_floors_metres_into_kilometre_cells(self):
        self.assertEqual(cell_of_position((150_999, 150_000)), (150, 150))
        self.assertEqual(cell_of_position((151_000, 149_999)), (151, 149))


if __name__ == "__main__":
    unittest.main()
