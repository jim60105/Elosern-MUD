"""Party window 系譜 tab browser acceptance (webclient-party-lineage-tab).

Two deterministic journeys on the shared managed server: the L hotkey
opens the party window on its 系譜 tab, where the committed ``lineage`` panel
renders its graph list (root name, node diamonds, owned/total) and the
selected graph drawn by depth (per-node levels, 見頂, XP meters, labelled
edges and prerequisite lines, all read verbatim from the payload); and an
unavailable payload renders only the registry reason with no invented graph.
Fixed injected snapshots; no live LLM, Stable Diffusion, or other network
service.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from ._journey_support import _inject_snapshot, _wait_mode


def _lineage_node(
    skill_key: str,
    display_name_zh: str,
    *,
    owned: bool,
    usable: bool,
    ready: bool,
    level: int,
    xp_into_level: float,
    xp_to_next_level: float,
    capped: bool,
    depth: int,
    prereq_text_zh: str = "",
) -> dict:
    """One schema-valid lineage node (exact field set of the panel contract)."""
    return {
        "skill_key": skill_key,
        "display_name_zh": display_name_zh,
        "owned": owned,
        "usable": usable,
        "ready": ready,
        "level": level,
        "xp_into_level": xp_into_level,
        "xp_to_next_level": xp_to_next_level,
        "capped": capped,
        "prereq_text_zh": prereq_text_zh,
        "depth": depth,
    }


def _available_lineage_panel() -> dict:
    """A schema-valid available lineage payload: one graph, three nodes.

    The whole graph is locally authored payload data — the client renders it
    verbatim and never resolves these keys against a registry — so its
    identifiers and displays are fixture-authored ``t_`` values, not shipped
    catalog rows.
    """
    root_key, root_name = CHAIN_ROOT
    mid_key, mid_name = CHAIN_MID
    leaf_key, leaf_name = CHAIN_LEAF
    return {
        "schema_version": 2,
        "available": True,
        "kind": "lineage",
        "completed_count": 0,
        "total_count": 1,
        "graphs": [
            {
                "graph_id": root_key,
                "group_label_zh": "燼",
                "root_keys": [root_key],
                "owned_count": 2,
                "total_count": 3,
                "consumed": False,
                "nodes": [
                    _lineage_node(
                        root_key,
                        root_name,
                        owned=True,
                        usable=True,
                        ready=False,
                        level=1,
                        xp_into_level=23.0,
                        xp_to_next_level=27.0,
                        capped=False,
                        depth=0,
                    ),
                    _lineage_node(
                        mid_key,
                        mid_name,
                        owned=True,
                        usable=True,
                        ready=False,
                        level=3,
                        xp_into_level=0.0,
                        xp_to_next_level=0.0,
                        capped=True,
                        depth=1,
                    ),
                    _lineage_node(
                        leaf_key,
                        leaf_name,
                        owned=False,
                        usable=False,
                        ready=False,
                        level=0,
                        xp_into_level=0.0,
                        xp_to_next_level=50.0,
                        capped=False,
                        depth=2,
                        prereq_text_zh=f"需「{mid_name} Lv.3」",
                    ),
                ],
                "edges": [
                    {
                        "from_key": root_key,
                        "to_key": mid_key,
                        "min_level": 1,
                    },
                    {
                        "from_key": mid_key,
                        "to_key": leaf_key,
                        "min_level": 3,
                    },
                ],
            }
        ],
    }


#: Authored graph-node identities (key, display) for the injected payload.
CHAIN_ROOT = ("t_lineage_root_arrow", "燼影箭")
CHAIN_MID = ("t_lineage_mid_burst", "燼心爆")
CHAIN_LEAF = ("t_lineage_leaf_wave", "燼浪濤")


def _unavailable_lineage_panel() -> dict:
    """A schema-valid unavailable lineage payload (common unavailable form)."""
    return {
        "schema_version": 2,
        "available": False,
        "reason": {
            "code": "lineage_unavailable",
            "message": "技能系譜目前無法顯示",
        },
    }


def _commander_party_panel() -> dict:
    """A committed party v3 panel of the commander alone, the viewed member."""
    return {
        "schema_version": 3,
        "available": True,
        "general_quota": {"used": 0, "limit": 4},
        "viewed_member_id": 42,
        "slots": [{
            "identity": 42, "display_name": "燼行者", "portrait_ref": None,
            "hp_current": 100, "hp_maximum": 100, "mp_current": 50, "mp_maximum": 50,
            "sp_current": 40, "sp_maximum": 40, "role": "commander", "knocked_out": False,
            "unread": False, "bond_stage": None, "membership": None,
        }],
    }


class PartyLineageTabBrowserTest(BrowserAcceptanceTest):
    """The party window's 系譜 tab on the shared managed server."""

    @covers_requirement(
        "skill-lineage-panel::the-party-window-lineage-tab-renders-the-graphs-from-the-view-alone",
        "webclient-party-window::the-lineage-list-groups-graphs-with-node-diamonds",
        "webclient-party-window::the-lineage-detail-draws-the-real-graph",
    )
    def test_lineage_tab_renders_the_committed_ledger_verbatim(self):
        """The tool opens 系譜; the list row and the drawn graph match the payload."""
        page = self.logged_in_page((1451, 790))
        _inject_snapshot(
            page,
            {"party": _commander_party_panel(), "lineage": _available_lineage_panel()},
            mode="exploration",
        )
        _wait_mode(page, "exploration")

        # The L window hotkey opens the party window on its 系譜 tab
        # (webclient-main-navigation-hotkeys), with the focused 隊伍 entry as
        # its opener.
        opener = page.locator('[data-nav-slot="party"]')
        opener.focus()
        page.keyboard.press("l")
        page.wait_for_selector('[data-testid="party-lineage-tab"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="party-window"]').get_attribute("data-tab"), "lineage"
        )
        self.assertEqual(
            page.locator('[data-testid="party-lineage-tab__summary"]').inner_text(),
            "已完成 0 / 1 樹",
        )

        root_key, root_name = CHAIN_ROOT
        mid_key, _mid_name = CHAIN_MID
        leaf_key, _leaf_name = CHAIN_LEAF
        row = page.locator(f'[data-testid="party-lineage-tab__row"][data-graph="{root_key}"]')
        self.assertEqual(row.locator('[data-testid="party-lineage-tab__row-name"]').inner_text(), root_name)
        self.assertEqual(row.locator('[data-testid="party-lineage-tab__count"]').inner_text(), "2 / 3")
        self.assertEqual(
            [
                row.locator('[data-testid="party-lineage-tab__pip"]').nth(i).get_attribute("data-state")
                for i in range(3)
            ],
            ["owned", "capped", "locked"],
        )

        def node(key):
            return page.locator(f'[data-testid="party-lineage-tab__node"][data-key="{key}"]')

        self.assertEqual(
            node(root_key).locator('[data-testid="party-lineage-tab__node-meter"]').inner_text(),
            "23/50 → 下一階",
        )
        self.assertEqual(
            node(mid_key).locator('[data-testid="party-lineage-tab__node-growth"]').inner_text(), "見頂"
        )
        self.assertEqual(
            node(leaf_key).locator('[data-testid="party-lineage-tab__node-prereq"]').inner_text(),
            f"需「{CHAIN_MID[1]} Lv.3」",
        )
        self.assertEqual(node(leaf_key).get_attribute("data-state"), "locked")
        self.assertEqual(
            page.locator('[data-testid="party-lineage-tab__edge-label"]').all_inner_texts(),
            ["Lv 1", "Lv 3"],
        )
        # The nodes stand one depth row apart, top to bottom, inside the canvas.
        tops = [node(key).bounding_box()["y"] for key in (root_key, mid_key, leaf_key)]
        self.assertLess(tops[0], tops[1])
        self.assertLess(tops[1], tops[2])
        self.assertEqual(page.evaluate("() => document.querySelectorAll('.lineage-chain__meter').length"), 0)

        # Closing the window returns focus to the 隊伍 entry it was opened from.
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"party-window\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.dataset.navSlot"),
            "party",
        )

    @covers_requirement("skill-lineage-panel::the-party-window-lineage-tab-renders-the-graphs-from-the-view-alone")
    def test_unavailable_lineage_renders_only_the_registry_reason(self):
        """The unavailable payload renders its reason line and no placeholder graph."""
        page = self.logged_in_page((1451, 790))
        _inject_snapshot(
            page,
            {"party": _commander_party_panel(), "lineage": _unavailable_lineage_panel()},
            mode="exploration",
        )
        _wait_mode(page, "exploration")

        page.locator('[data-nav-slot="party"]').focus()
        page.keyboard.press("l")
        page.wait_for_selector('[data-testid="party-lineage-tab"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="party-window__tab-unavailable"]').inner_text(),
            "技能系譜目前無法顯示",
        )
        self.assertEqual(
            page.locator('[data-testid="party-lineage-tab__row"]').count(),
            0,
            "the client invents no placeholder graph",
        )
        self.assertEqual(page.locator('[data-testid="party-lineage-tab__node"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="party-lineage-tab__summary"]').count(), 0)
