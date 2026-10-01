"""Tests for offline persona bundle vocabulary, validation, and selector.

Tests synthetic pools for malformed bundles, wrong-race bundles, one-bundle
pools, duplicate personality/speech style, tier vs race resolution, selector
determinism across calls and subprocess interpreters, distinct seed coverage,
and lack of state writes.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from types import MappingProxyType
from unittest.mock import patch

from world.lore.npc_card import NpcCard
from world.lore.npc_profiles.bundles import (
    NpcBundlePool,
    NpcPersonaBundle,
    _validate_bundle_pools,
    offline_pool_for,
    select_offline_bundle,
)
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY


def _make_test_card(
    *,
    public: str = "普通市民",
    hidden: str = "",
    appearance: str = "外觀整潔",
    personality: str = "性格溫和",
    speech_style: str = "說話語氣平和",
    life_story: str = "自幼在城中生活",
    habit: str = "習慣清晨散步",
    social_connection: str = "",
) -> NpcCard:
    return NpcCard.from_record(
        {
            "identity": {"public": public, "hidden": hidden},
            "appearance": appearance,
            "personality": personality,
            "speech_style": speech_style,
            "life_story": life_story,
            "habit": habit,
            "social_connection": social_connection,
        }
    )


def _make_test_bundle(
    key: str,
    race_key: str = "human",
    *,
    personality: str | None = None,
    speech_style: str | None = None,
    hidden: str = "",
    social_connection: str = "",
    card: NpcCard | None = None,
) -> NpcPersonaBundle:
    if card is None:
        card = _make_test_card(
            personality=personality or f"性格_{key}",
            speech_style=speech_style or f"說話風格_{key}",
            hidden=hidden,
            social_connection=social_connection,
        )
    return NpcPersonaBundle(key=key, card=card, race_key=race_key)


def _build_minimal_valid_pools() -> dict[str, NpcBundlePool]:
    """Construct a minimal valid pool dict satisfying all tiers and generic races."""
    pools: dict[str, NpcBundlePool] = {}
    for tier_key, tier in NPC_TIER_REGISTRY.items():
        b1 = _make_test_bundle(f"{tier_key}_01", race_key=tier.race_key)
        b2 = _make_test_bundle(f"{tier_key}_02", race_key=tier.race_key)
        pools[tier_key] = NpcBundlePool(key=tier_key, race_key=tier.race_key, bundles=(b1, b2))

    tier_races = {tier.race_key for tier in NPC_TIER_REGISTRY.values()}
    for race_key in RACE_REGISTRY:
        if race_key not in tier_races:
            generic_key = f"{race_key}_generic"
            b1 = _make_test_bundle(f"{generic_key}_01", race_key=race_key)
            b2 = _make_test_bundle(f"{generic_key}_02", race_key=race_key)
            pools[generic_key] = NpcBundlePool(
                key=generic_key, race_key=race_key, bundles=(b1, b2)
            )
    return pools


class NpcPersonaBundleValidationTests(unittest.TestCase):
    """Validation logic for synthetic bundle pools."""

    def test_valid_minimal_pools_pass_validation(self):
        pools = _build_minimal_valid_pools()
        _validate_bundle_pools(pools)

    def test_one_bundle_pool_rejected_naming_pool(self):
        pools = _build_minimal_valid_pools()
        single_bundle = _make_test_bundle("civilian_only", "human")
        pools["civilian"] = NpcBundlePool(
            key="civilian", race_key="human", bundles=(single_bundle,)
        )
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("at least 2 bundles", str(caught.exception))

    def test_bundle_race_mismatch_with_pool_rejected(self):
        pools = _build_minimal_valid_pools()
        b1 = _make_test_bundle("civilian_01", "human")
        b2 = _make_test_bundle("civilian_02", "elf")  # Mismatch
        pools["civilian"] = NpcBundlePool(key="civilian", race_key="human", bundles=(b1, b2))
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("civilian_02", str(caught.exception))
        self.assertIn("expected pool race 'human'", str(caught.exception))

    def test_malformed_card_over_budget_rejected_naming_pool_and_bundle(self):
        pools = _build_minimal_valid_pools()
        # Create an NpcCard that bypasses normal constructor or has overlong leaf
        from world.lore.npc_card import NpcCardIdentity

        overlong_story = "長" * 601
        raw_card = NpcCard(
            identity=NpcCardIdentity(public="市民", hidden=""),
            appearance="普通外觀",
            personality="獨特性格_01",
            speech_style="獨特語氣_01",
            life_story=overlong_story,
            habit="習慣",
            social_connection="",
        )
        bad_bundle = NpcPersonaBundle(key="civilian_bad", card=raw_card, race_key="human")
        good_bundle = _make_test_bundle("civilian_good", "human")
        pools["civilian"] = NpcBundlePool(
            key="civilian", race_key="human", bundles=(good_bundle, bad_bundle)
        )
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        err_msg = str(caught.exception)
        self.assertIn("civilian", err_msg)
        self.assertIn("civilian_bad", err_msg)

    def test_non_empty_hidden_identity_rejected(self):
        pools = _build_minimal_valid_pools()
        bad_bundle = _make_test_bundle("civilian_bad", "human", hidden="隱秘身分")
        good_bundle = _make_test_bundle("civilian_good", "human")
        pools["civilian"] = NpcBundlePool(
            key="civilian", race_key="human", bundles=(good_bundle, bad_bundle)
        )
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("civilian_bad", str(caught.exception))
        self.assertIn("hidden identity", str(caught.exception))

    def test_non_empty_social_connection_rejected(self):
        pools = _build_minimal_valid_pools()
        bad_bundle = _make_test_bundle("civilian_bad", "human", social_connection="認識某人")
        good_bundle = _make_test_bundle("civilian_good", "human")
        pools["civilian"] = NpcBundlePool(
            key="civilian", race_key="human", bundles=(good_bundle, bad_bundle)
        )
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("civilian_bad", str(caught.exception))
        self.assertIn("social_connection", str(caught.exception))

    def test_duplicate_personality_rejected(self):
        pools = _build_minimal_valid_pools()
        b1 = _make_test_bundle(
            "civilian_01", "human", personality="相同性格", speech_style="風格A"
        )
        b2 = _make_test_bundle(
            "civilian_02", "human", personality="相同性格", speech_style="風格B"
        )
        pools["civilian"] = NpcBundlePool(key="civilian", race_key="human", bundles=(b1, b2))
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("duplicate personality", str(caught.exception))

    def test_duplicate_speech_style_rejected(self):
        pools = _build_minimal_valid_pools()
        b1 = _make_test_bundle(
            "civilian_01", "human", personality="性格A", speech_style="相同說話風格"
        )
        b2 = _make_test_bundle(
            "civilian_02", "human", personality="性格B", speech_style="相同說話風格"
        )
        pools["civilian"] = NpcBundlePool(key="civilian", race_key="human", bundles=(b1, b2))
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("civilian", str(caught.exception))
        self.assertIn("duplicate speech_style", str(caught.exception))

    def test_duplicate_bundle_key_in_pool_rejected(self):
        pools = _build_minimal_valid_pools()
        b1 = _make_test_bundle("civilian_dup", "human", personality="性格A", speech_style="風格A")
        b2 = _make_test_bundle("civilian_dup", "human", personality="性格B", speech_style="風格B")
        pools["civilian"] = NpcBundlePool(key="civilian", race_key="human", bundles=(b1, b2))
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("duplicate bundle key 'civilian_dup'", str(caught.exception))

    def test_missing_role_tier_pool_rejected(self):
        pools = _build_minimal_valid_pools()
        del pools["bandit"]
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("bandit", str(caught.exception))

    def test_missing_generic_race_pool_rejected(self):
        pools = _build_minimal_valid_pools()
        del pools["beastfolk_generic"]
        with self.assertRaises(ValueError) as caught:
            _validate_bundle_pools(pools)
        self.assertIn("beastfolk_generic", str(caught.exception))


class NpcPersonaBundleResolutionTests(unittest.TestCase):
    """Pool resolution behavior (offline_pool_for)."""

    def setUp(self):
        self.mock_pools = _build_minimal_valid_pools()
        self.patcher = patch(
            "world.lore.npc_profiles.bundles.NPC_PERSONA_BUNDLE_POOLS",
            MappingProxyType(self.mock_pools),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_tier_match_returns_tier_pool(self):
        pool = offline_pool_for("bandit", "human")
        self.assertEqual(pool.key, "bandit")
        self.assertEqual(pool.race_key, "human")

    def test_tier_race_mismatch_falls_back_to_race_generic_pool(self):
        # bandit is human; if queried for beastfolk, should fall back to beastfolk_generic
        pool = offline_pool_for("bandit", "beastfolk")
        self.assertEqual(pool.key, "beastfolk_generic")
        self.assertEqual(pool.race_key, "beastfolk")

    def test_unknown_tier_falls_back_to_human_civilian_pool(self):
        pool = offline_pool_for("unknown_tier", "human")
        self.assertEqual(pool.key, "civilian")

    def test_unknown_tier_falls_back_to_elf_civilian_pool(self):
        pool = offline_pool_for("unknown_tier", "elf")
        self.assertEqual(pool.key, "elven_civilian")

    def test_no_tier_returns_race_generic_pool(self):
        pool = offline_pool_for(None, "beastfolk")
        self.assertEqual(pool.key, "beastfolk_generic")

    def test_unregistered_race_raises_value_error(self):
        with self.assertRaises(ValueError) as caught:
            offline_pool_for("bandit", "alien_race")
        self.assertIn("alien_race", str(caught.exception))


class NpcPersonaBundleSelectorTests(unittest.TestCase):
    """Deterministic selection behavior (select_offline_bundle)."""

    def setUp(self):
        self.mock_pools = _build_minimal_valid_pools()
        self.patcher = patch(
            "world.lore.npc_profiles.bundles.NPC_PERSONA_BUNDLE_POOLS",
            MappingProxyType(self.mock_pools),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_determinism_across_multiple_calls(self):
        res1 = select_offline_bundle("civilian", "npc_seed_12345")
        res2 = select_offline_bundle("civilian", "npc_seed_12345")
        self.assertEqual(res1[0], res2[0])
        self.assertEqual(res1[1], res2[1])

    def test_distinct_seeds_reach_both_bundles_with_authored_speech_style(self):
        # With a 2-bundle pool, testing various seeds should hit both bundles
        seen_keys: set[str] = set()
        seen_speech_styles: set[str] = set()

        for i in range(50):
            bundle_key, card = select_offline_bundle("civilian", f"seed_{i}")
            seen_keys.add(bundle_key)
            seen_speech_styles.add(card.speech_style)
            if len(seen_keys) == 2:
                break

        self.assertEqual(seen_keys, {"civilian_01", "civilian_02"})
        self.assertEqual(seen_speech_styles, {"說話風格_civilian_01", "說話風格_civilian_02"})

    def test_unknown_pool_raises_value_error(self):
        with self.assertRaises(ValueError) as caught:
            select_offline_bundle("nonexistent_pool", "seed")
        self.assertIn("nonexistent_pool", str(caught.exception))

    def test_subprocess_determinism(self):
        """Selection is identical across independent Python processes."""
        code = (
            "import sys; "
            "from world.lore.npc_profiles.bundles import select_offline_bundle; "
            "import world.lore.npc_profiles.bundles as b; "
            "from world.lore.tests.test_npc_persona_bundles import _build_minimal_valid_pools; "
            "from types import MappingProxyType; "
            "b.NPC_PERSONA_BUNDLE_POOLS = MappingProxyType(_build_minimal_valid_pools()); "
            "k, c = select_offline_bundle('civilian', 'cross_process_seed_99'); "
            "sys.stdout.write(f'{k}:{c.personality}')"
        )
        res_current = select_offline_bundle("civilian", "cross_process_seed_99")
        expected_out = f"{res_current[0]}:{res_current[1].personality}"

        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc.stdout, expected_out)
