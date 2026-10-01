"""Data-contract test: guild registry content contract
Self-consistency checks for guild reward bands."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.guild import (
    GUILD_BRANCH_REGISTRY,
    GUILD_RANK_REGISTRY,
    GuildBranch,
    GuildRank,
    validate_guild_npc_identities,
)


class GuildRegistryTests(unittest.TestCase):
    @covers_requirement("lore-registries::guildrank-registry-provides-ordered-reward-bands-in-copper")
    def test_rank_order_and_reward_ladder(self):
        ranks = sorted(GUILD_RANK_REGISTRY.values(), key=lambda rank: rank.order)
        self.assertEqual([rank.key for rank in ranks], ["F", "E", "D", "C", "B", "A", "S"])
        self.assertEqual([rank.order for rank in ranks], list(range(1, 8)))
        for rank, next_rank in zip(ranks, ranks[1:]):
            self.assertIsInstance(rank.reward_min_copper, int)
            self.assertIsInstance(rank.reward_max_copper, int)
            self.assertGreater(rank.reward_max_copper, rank.reward_min_copper)
            self.assertEqual(rank.reward_max_copper, next_rank.reward_min_copper)
        self.assertIsNone(ranks[-1].reward_max_copper)
        self.assertIsInstance(ranks[-1].reward_min_copper, int)


class GuildNPCIdentityTests(unittest.TestCase):
    """Authored examiner/host identities fail closed at load (design D4)."""

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_invalid_examiner_title_is_named_by_row_and_field(self):
        bad = dict(GUILD_RANK_REGISTRY)
        row = bad["D"]
        bad["D"] = GuildRank(
            row.key, row.order, row.reward_min_copper, row.reward_max_copper,
            row.description, row.title_key, row.examiner_name, "含\x00控制的稱號",
            row.examiner_profile_key,
        )
        with self.assertRaises(ValueError) as caught:
            validate_guild_npc_identities(ranks=bad, branches={})
        message = str(caught.exception)
        self.assertIn("guild rank D", message)
        self.assertIn("examiner_title", message)

    def test_invalid_branch_host_name_is_named_by_row_and_field(self):
        row = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        bad = {
            "k": GuildBranch(row.key, row.display_name_zh, "  ", row.host_title, row.anchor_key)
        }
        with self.assertRaises(ValueError) as caught:
            validate_guild_npc_identities(ranks={}, branches=bad)
        self.assertIn("invalid host_name", str(caught.exception))

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_missing_identity_fields_reject_construction(self):
        # Examiner/host identity fields are required without defaults.
        import dataclasses

        fields = {field.name: None for field in dataclasses.fields(GuildRank)}
        fields.pop("examiner_name")
        fields.pop("examiner_title")
        with self.assertRaises(TypeError):
            GuildRank(**fields)

    def test_missing_or_unregistered_examiner_profile_key_is_named_by_rank(self):
        # npc-persona-content-altoria-guild D6: every validated rank must name
        # a registered examiner profile; the error names the rank and field.
        import dataclasses

        row = GUILD_RANK_REGISTRY["D"]
        for key in (None, "t_no_such_examiner_profile"):
            with self.subTest(examiner_profile_key=key):
                bad = {"D": dataclasses.replace(row, examiner_profile_key=key)}
                with self.assertRaises(ValueError) as caught:
                    validate_guild_npc_identities(ranks=bad, branches={})
                message = str(caught.exception)
                self.assertIn("guild rank D", message)
                self.assertIn("examiner_profile_key", message)

    def test_examiner_profile_with_voice_lines_is_rejected(self):
        # An examiner is a combat opponent with no dialogue capability, so the
        # profile a rank names must author no voice lines.
        import dataclasses
        from unittest import mock

        from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
        from world.lore.npc_profiles.shape import NpcVoiceLines

        row = GUILD_RANK_REGISTRY["D"]
        speaking = dataclasses.replace(
            NPC_PROFILE_REGISTRY[row.examiner_profile_key],
            key="t_speaking_examiner",
            voice=NpcVoiceLines(misunderstood="「嗯？」"),
        )
        registry = {**NPC_PROFILE_REGISTRY, "t_speaking_examiner": speaking}
        with mock.patch(
            "world.lore.npc_profiles.NPC_PROFILE_REGISTRY", registry
        ):
            with self.assertRaises(ValueError) as caught:
                validate_guild_npc_identities(
                    ranks={
                        "D": dataclasses.replace(
                            row, examiner_profile_key="t_speaking_examiner"
                        )
                    },
                    branches={},
                )
        self.assertIn("voice lines", str(caught.exception))

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_shipped_rows_load_clean(self):
        # The module-level call already ran at import; an explicit re-run is a
        # no-op proof that every shipped row passes both shared validators.
        validate_guild_npc_identities()
