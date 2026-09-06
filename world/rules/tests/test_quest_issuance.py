"""Focused unit tests for the quest issuance registry and issuer key grammar."""

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.lore.items import ITEM_REGISTRY, ItemDefinition
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestStage,
)
from world.quests.tests._fixtures import QuestRegistryIsolation, quest, register
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    get_guild_offer,
    register_guild_offer,
)
from world.rules.quest_issuance import (
    MAX_ISSUER_KEY_LENGTH,
    QUEST_ISSUANCE_REGISTRY,
    IssuerKeyError,
    ParsedIssuerKey,
    QuestIssuance,
    QuestIssuanceError,
    Settlement,
    guild_issuer_key,
    npc_issuer_key,
    parse_issuer_key,
    register_quest_issuance,
    resolve_issuance,
)

ALTORIA_BRANCH = "guild_branch_altoria"


def _sample_reward(copper: int = 50, merit: int = 0, item_key: str = "healing_potion") -> QuestReward:
    return QuestReward(
        copper=copper,
        items=(ItemQuantity(item_key, 1),),
        merit=merit,
    )


class QuestIssuanceIsolationMixin:
    """Isolate QUEST_ISSUANCE_REGISTRY and GUILD_OFFER_REGISTRY across tests."""

    def setUp(self):
        super().setUp()
        self._issuance_items = list(QUEST_ISSUANCE_REGISTRY.items())
        self._guild_offer_items = list(GUILD_OFFER_REGISTRY.items())
        self.addCleanup(self._restore_registries)

    def _restore_registries(self):
        QUEST_ISSUANCE_REGISTRY.clear()
        QUEST_ISSUANCE_REGISTRY.update(self._issuance_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._guild_offer_items)


class IssuerKeyGrammarTests(unittest.TestCase):
    """Tests for parse_issuer_key, guild_issuer_key, and npc_issuer_key."""

    @covers_requirement("quest-issuance::an-issuer-key-is-a-namespaced-validated-identity")
    def test_parse_valid_guild_key(self):
        parsed = parse_issuer_key("guild:guild_branch_altoria")
        self.assertEqual(
            parsed,
            ParsedIssuerKey(namespace="guild", remainder="guild_branch_altoria", entity_pk=None),
        )

    def test_parse_valid_npc_authored_key(self):
        parsed = parse_issuer_key("npc:grey_granny")
        self.assertEqual(
            parsed,
            ParsedIssuerKey(namespace="npc", remainder="grey_granny", entity_pk=None),
        )

    def test_parse_valid_npc_pk_key(self):
        parsed = parse_issuer_key("npc:#1234")
        self.assertEqual(
            parsed,
            ParsedIssuerKey(namespace="npc", remainder="#1234", entity_pk=1234),
        )

    def test_parse_boundary_length_key(self):
        # exactly MAX_ISSUER_KEY_LENGTH
        key = "npc:" + "a" * (MAX_ISSUER_KEY_LENGTH - 4)
        self.assertEqual(len(key), MAX_ISSUER_KEY_LENGTH)
        parsed = parse_issuer_key(key)
        self.assertEqual(parsed.namespace, "npc")
        self.assertEqual(parsed.remainder, "a" * (MAX_ISSUER_KEY_LENGTH - 4))

    def test_parse_rejects_over_length_key(self):
        key = "npc:" + "a" * (MAX_ISSUER_KEY_LENGTH - 3)
        self.assertEqual(len(key), MAX_ISSUER_KEY_LENGTH + 1)
        with self.assertRaises(IssuerKeyError) as cm:
            parse_issuer_key(key)
        self.assertIn("exceeds maximum length", str(cm.exception))

    def test_parse_rejects_non_string(self):
        for bad in (123, None, ["guild:branch"], True):
            with self.subTest(bad=bad):
                with self.assertRaises(IssuerKeyError):
                    parse_issuer_key(bad)

    def test_parse_rejects_empty_string(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key("")

    def test_parse_rejects_missing_separator(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key("guild_branch_altoria")

    def test_parse_rejects_multiple_separators(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key("npc:grey:granny")

    def test_parse_rejects_empty_namespace(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key(":grey_granny")

    def test_parse_rejects_empty_remainder(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key("npc:")

    def test_parse_rejects_unknown_namespace(self):
        with self.assertRaises(IssuerKeyError):
            parse_issuer_key("monster:goblin")

    def test_parse_rejects_invalid_npc_pk_forms(self):
        for bad_remainder in ("#", "#0", "#-1", "#abc", "#12a", "# 42", "#１２３"):
            with self.subTest(bad=bad_remainder):
                with self.assertRaises(IssuerKeyError):
                    parse_issuer_key(f"npc:{bad_remainder}")

    def test_parse_rejects_digit_only_npc_authored_key(self):
        for digit_key in ("npc:0", "npc:1234", "npc:999999"):
            with self.subTest(key=digit_key):
                with self.assertRaises(IssuerKeyError):
                    parse_issuer_key(digit_key)

    def test_guild_issuer_key_helper(self):
        self.assertEqual(guild_issuer_key(ALTORIA_BRANCH), f"guild:{ALTORIA_BRANCH}")
        with self.assertRaises(IssuerKeyError):
            guild_issuer_key("")
        with self.assertRaises(IssuerKeyError):
            guild_issuer_key(None)

    def test_npc_issuer_key_helper(self):
        self.assertEqual(npc_issuer_key(content_key="grey_granny"), "npc:grey_granny")
        self.assertEqual(npc_issuer_key(pk=42), "npc:#42")

        # Rejects neither or both
        with self.assertRaises(IssuerKeyError):
            npc_issuer_key()
        with self.assertRaises(IssuerKeyError):
            npc_issuer_key(content_key="grey_granny", pk=42)

        # Rejects boolean PK or negative PK
        with self.assertRaises(IssuerKeyError):
            npc_issuer_key(pk=True)
        with self.assertRaises(IssuerKeyError):
            npc_issuer_key(pk=0)
        with self.assertRaises(IssuerKeyError):
            npc_issuer_key(pk=-5)


class SettlementVocabularyTests(unittest.TestCase):
    """Tests for the Settlement closed vocabulary."""

    @covers_requirement("quest-issuance::settlement-is-a-closed-two-value-vocabulary")
    def test_settlement_members(self):
        self.assertEqual(set(Settlement), {Settlement.COUNTER, Settlement.AUTO})
        self.assertEqual(Settlement.COUNTER.value, "counter")
        self.assertEqual(Settlement.AUTO.value, "auto")

    def test_settlement_construction_rejects_unknown_string(self):
        with self.assertRaises(ValueError):
            Settlement("manual")


class QuestIssuanceValueTests(QuestRegistryIsolation, unittest.TestCase):
    """Tests for QuestIssuance creation, validation, immutability, and merit rule."""

    def setUp(self):
        super().setUp()
        self.def_key = "test_issuance_quest"
        register(quest(self.def_key))

    @covers_requirement("quest-issuance::a-quest-issuance-is-an-immutable-value-binding-one-definition-to-one-issuer")
    def test_valid_npc_issuance_creation_and_immutability(self):
        reward = _sample_reward(copper=100, merit=0)
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=reward,
            settlement=Settlement.AUTO,
        )
        self.assertEqual(issuance.definition_key, self.def_key)
        self.assertEqual(issuance.issuer_key, "npc:grey_granny")
        self.assertEqual(issuance.reward, reward)
        self.assertEqual(issuance.settlement, Settlement.AUTO)

        # Frozen dataclass raises on field mutation
        with self.assertRaises(FrozenInstanceError):
            issuance.settlement = Settlement.COUNTER

    def test_unregistered_definition_key_rejects(self):
        with self.assertRaises(QuestIssuanceError) as cm:
            QuestIssuance(
                definition_key="nonexistent_definition",
                issuer_key="npc:grey_granny",
                reward=_sample_reward(copper=100, merit=0),
                settlement=Settlement.AUTO,
            )
        self.assertIn("unknown quest definition", str(cm.exception))

    def test_malformed_issuer_key_rejects(self):
        with self.assertRaises(IssuerKeyError):
            QuestIssuance(
                definition_key=self.def_key,
                issuer_key="bad:key:here",
                reward=_sample_reward(copper=100, merit=0),
                settlement=Settlement.AUTO,
            )

    def test_plain_string_settlement_rejects(self):
        # Strict closed vocabulary: plain string is rejected even if equal to enum value
        for plain in ("auto", "counter"):
            with self.subTest(plain=plain):
                with self.assertRaises(QuestIssuanceError) as cm:
                    QuestIssuance(
                        definition_key=self.def_key,
                        issuer_key="npc:grey_granny",
                        reward=_sample_reward(copper=100, merit=0),
                        settlement=plain,  # type: ignore[arg-type]
                    )
                self.assertIn("Settlement enum member", str(cm.exception))

    @covers_requirement("quest-issuance::a-private-commission-never-grants-guild-merit")
    def test_npc_issuance_rejects_non_zero_merit(self):
        with self.assertRaises(QuestIssuanceError) as cm:
            QuestIssuance(
                definition_key=self.def_key,
                issuer_key="npc:grey_granny",
                reward=_sample_reward(copper=100, merit=10),
                settlement=Settlement.AUTO,
            )
        self.assertIn("cannot grant guild merit", str(cm.exception))

    def test_guild_issuance_permits_merit(self):
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key=f"guild:{ALTORIA_BRANCH}",
            reward=_sample_reward(copper=100, merit=25),
            settlement=Settlement.COUNTER,
        )
        self.assertEqual(issuance.reward.merit, 25)

    def test_invalid_reward_surface_rejects(self):
        # negative copper
        with self.assertRaises(QuestIssuanceError):
            QuestIssuance(
                definition_key=self.def_key,
                issuer_key="npc:grey_granny",
                reward=_sample_reward(copper=-1),
                settlement=Settlement.AUTO,
            )
        # unknown item
        with self.assertRaises(QuestIssuanceError):
            QuestIssuance(
                definition_key=self.def_key,
                issuer_key="npc:grey_granny",
                reward=_sample_reward(item_key="nonexistent_item_key_xyz"),
                settlement=Settlement.AUTO,
            )
        # duplicate items
        with self.assertRaises(QuestIssuanceError):
            QuestIssuance(
                definition_key=self.def_key,
                issuer_key="npc:grey_granny",
                reward=QuestReward(
                    copper=50,
                    items=(ItemQuantity("healing_potion", 1), ItemQuantity("healing_potion", 2)),
                    merit=0,
                ),
                settlement=Settlement.AUTO,
            )


class QuestIssuanceRegistryTests(QuestIssuanceIsolationMixin, QuestRegistryIsolation, unittest.TestCase):
    """Tests for QUEST_ISSUANCE_REGISTRY and register_quest_issuance."""

    def setUp(self):
        super().setUp()
        self.def_key = "test_issuance_quest_reg"
        register(quest(self.def_key))

    @covers_requirement("quest-issuance::the-issuance-registry-stores-private-commissions-idempotently")
    def test_register_npc_issuance_success_and_logging(self):
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=_sample_reward(copper=50, merit=0),
            settlement=Settlement.AUTO,
        )
        with patch("world.rules.quest_issuance.log_info") as mock_log:
            register_quest_issuance(issuance)
            mock_log.assert_called_once_with(
                "quest_issuance_registered",
                context={"quest": self.def_key, "issuer": "npc:grey_granny"},
            )
        self.assertEqual(
            QUEST_ISSUANCE_REGISTRY[(self.def_key, "npc:grey_granny")],
            issuance,
        )

    def test_register_identical_issuance_is_idempotent_no_op(self):
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=_sample_reward(copper=50, merit=0),
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance)

        # Second identical call does not raise and does not re-log
        with patch("world.rules.quest_issuance.log_info") as mock_log:
            register_quest_issuance(issuance)
            mock_log.assert_not_called()
        self.assertEqual(
            QUEST_ISSUANCE_REGISTRY[(self.def_key, "npc:grey_granny")],
            issuance,
        )

    def test_register_conflicting_issuance_raises_without_overwriting(self):
        issuance1 = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=_sample_reward(copper=50, merit=0),
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance1)

        conflicting = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=_sample_reward(copper=100, merit=0),
            settlement=Settlement.AUTO,
        )
        with self.assertRaises(QuestIssuanceError) as cm:
            register_quest_issuance(conflicting)
        self.assertIn("conflicting issuance already registered", str(cm.exception))
        # Original remains intact
        self.assertEqual(
            QUEST_ISSUANCE_REGISTRY[(self.def_key, "npc:grey_granny")],
            issuance1,
        )

    def test_register_guild_key_is_refused(self):
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key=f"guild:{ALTORIA_BRANCH}",
            reward=_sample_reward(copper=50, merit=10),
            settlement=Settlement.COUNTER,
        )
        with self.assertRaises(QuestIssuanceError) as cm:
            register_quest_issuance(issuance)
        self.assertIn("only stores npc-namespaced issuances", str(cm.exception))
        self.assertNotIn((self.def_key, f"guild:{ALTORIA_BRANCH}"), QUEST_ISSUANCE_REGISTRY)


class ResolveIssuanceSeamTests(QuestIssuanceIsolationMixin, QuestRegistryIsolation, unittest.TestCase):
    """Tests for resolve_issuance normalized read seam."""

    def setUp(self):
        super().setUp()
        self.def_key = "test_issuance_seam_quest"
        register(quest(self.def_key))

    @covers_requirement("quest-issuance::one-normalized-read-seam-resolves-an-issuance-for-any-issuer-kind")
    def test_resolve_guild_offer_hit(self):
        guild_reward = _sample_reward(copper=50, merit=25)
        offer = GuildQuestOffer(
            definition_key=self.def_key,
            issuer_branch_key=ALTORIA_BRANCH,
            reward=guild_reward,
        )
        register_guild_offer(offer)

        resolved = resolve_issuance(self.def_key, f"guild:{ALTORIA_BRANCH}")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.definition_key, self.def_key)
        self.assertEqual(resolved.issuer_key, f"guild:{ALTORIA_BRANCH}")
        self.assertEqual(resolved.reward, guild_reward)
        self.assertEqual(resolved.settlement, Settlement.COUNTER)

    def test_resolve_npc_commission_hit(self):
        npc_reward = _sample_reward(copper=80, merit=0)
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=npc_reward,
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance)

        resolved = resolve_issuance(self.def_key, "npc:grey_granny")
        self.assertEqual(resolved, issuance)

    def test_resolve_unregistered_identity_returns_none(self):
        self.assertIsNone(resolve_issuance(self.def_key, f"guild:{ALTORIA_BRANCH}"))
        self.assertIsNone(resolve_issuance(self.def_key, "npc:unregistered_npc"))

    def test_resolve_malformed_key_raises_parser_error(self):
        with self.assertRaises(IssuerKeyError):
            resolve_issuance(self.def_key, "invalid_no_colon")
        with self.assertRaises(IssuerKeyError):
            resolve_issuance(self.def_key, "unknown:branch")

    @covers_requirement("quest-issuance::the-guild-offer-surface-is-unchanged-by-the-issuer-layer")
    def test_guild_surface_untouched_and_independent(self):
        # Verify GUILD_OFFER_REGISTRY does not see npc issuances and vice versa
        npc_reward = _sample_reward(copper=80, merit=0)
        issuance = QuestIssuance(
            definition_key=self.def_key,
            issuer_key="npc:grey_granny",
            reward=npc_reward,
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance)

        self.assertNotIn((self.def_key, "npc:grey_granny"), GUILD_OFFER_REGISTRY)
        self.assertNotIn((self.def_key, "grey_granny"), GUILD_OFFER_REGISTRY)

        # Verify that get_guild_offer and register_guild_offer
        # preserve their exact contract, types, and idempotency
        guild_reward = _sample_reward(copper=50, merit=25)
        offer = GuildQuestOffer(
            definition_key=self.def_key,
            issuer_branch_key=ALTORIA_BRANCH,
            reward=guild_reward,
        )
        register_guild_offer(offer)
        fetched = get_guild_offer(self.def_key, ALTORIA_BRANCH)
        self.assertIsInstance(fetched, GuildQuestOffer)
        self.assertEqual(fetched, offer)

        # Idempotency
        register_guild_offer(offer)
        self.assertEqual(get_guild_offer(self.def_key, ALTORIA_BRANCH), offer)
