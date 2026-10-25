"""Data-contract test: social identity canonical tag model and reader/writer APIs."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.lore.social_identities import (
    MAX_SOCIAL_IDENTITIES,
    SOCIAL_IDENTITY_REGISTRY,
    SocialIdentity,
)
from world.rules.social_identity import (
    SocialIdentityError,
    read_social_identities,
    set_social_identities,
)


class SocialIdentityTagModelTests(EvenniaTestCase):
    """Test the <=8-key registry, pure reader, sole writer, and fail-closed state."""

    def test_registry_vocabulary_and_bounds(self):
        """Registry contains exact initial vocabulary and has <= 8 keys."""
        self.assertLessEqual(len(SOCIAL_IDENTITY_REGISTRY), MAX_SOCIAL_IDENTITIES)
        self.assertEqual(MAX_SOCIAL_IDENTITIES, 8)
        self.assertEqual(
            set(SOCIAL_IDENTITY_REGISTRY.keys()),
            {"noble", "clergy", "official", "adventurer"},
        )
        for key, identity in SOCIAL_IDENTITY_REGISTRY.items():
            self.assertIsInstance(identity, SocialIdentity)
            self.assertEqual(identity.key, key)
            self.assertTrue(identity.display_name_zh)

    def test_social_identity_dataclass_validation(self):
        """SocialIdentity rejects non-string or empty keys/labels."""
        with self.assertRaises(ValueError):
            SocialIdentity("", "標籤")
        with self.assertRaises(ValueError):
            SocialIdentity("key", "")
        with self.assertRaises(ValueError):
            SocialIdentity(123, "標籤")  # type: ignore

    @covers_requirement("social-identity::social-identity-is-explicit-typed-state")
    def test_read_missing_or_empty_is_empty_frozenset(self):
        """Missing or uninitialized social identity reads as empty frozenset, not commoner."""
        npc = MagicMock()
        npc.attributes.has.return_value = False
        self.assertEqual(read_social_identities(npc), frozenset())

        self.assertEqual(read_social_identities(None), frozenset())

        bare_obj = SimpleNamespace()
        self.assertEqual(read_social_identities(bare_obj), frozenset())

    def test_set_and_read_roundtrip(self):
        """Setting valid keys persists sorted unique tuple and reads as frozenset."""
        char = MagicMock()
        stored = {}

        def mock_add(key, val):
            stored[key] = val

        def mock_get(key):
            return stored.get(key)

        char.attributes.has.side_effect = lambda k: k in stored
        char.attributes.get.side_effect = mock_get
        char.attributes.add.side_effect = mock_add

        result = set_social_identities(char, ["clergy", "official"])
        self.assertEqual(result, frozenset({"clergy", "official"}))
        self.assertEqual(stored["social_identities"], ("clergy", "official"))
        self.assertEqual(read_social_identities(char), frozenset({"clergy", "official"}))

        # Accepts set or frozenset as input
        result2 = set_social_identities(char, frozenset({"noble"}))
        self.assertEqual(result2, frozenset({"noble"}))
        self.assertEqual(stored["social_identities"], ("noble",))
        self.assertEqual(read_social_identities(char), frozenset({"noble"}))

        # Setting empty iterable
        result3 = set_social_identities(char, ())
        self.assertEqual(result3, frozenset())
        self.assertEqual(stored["social_identities"], ())
        self.assertEqual(read_social_identities(char), frozenset())

    @covers_requirement("social-identity::identity-writes-follow-deterministic-construction")
    def test_set_rejects_invalid_inputs(self):
        """set_social_identities rejects unknown keys, non-strings, strings directly, non-iterables."""
        char = MagicMock()
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, "noble")  # direct string rejected
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, 123)  # non-iterable rejected
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, ["unknown_key"])
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, [True])  # bool rejected
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, ["noble", 123])
        with self.assertRaises(SocialIdentityError):
            set_social_identities(char, {"key": "val"})  # dict rejected
        with self.assertRaises(SocialIdentityError):
            set_social_identities(None, ["noble"])

    def test_fail_closed_corrupted_storage(self):
        """Corrupted storage (raw string, list with ints/bools, unknown keys) reads as empty frozenset."""
        char = MagicMock()
        char.attributes.has.return_value = True

        for bad in [
            "noble",
            123,
            {"noble": True},
            ["noble", "invalid_key"],
            ["noble", 123],
            [True, False],
            ("noble", None),
        ]:
            char.attributes.get.return_value = bad
            self.assertEqual(read_social_identities(char), frozenset())

    @covers_requirement(
        "social-identity::social-qualification-has-identical-meaning-across-sources"
    )
    @covers_requirement("social-identity::social-identity-is-explicit-typed-state")
    def test_persona_title_and_race_never_grant_identity(self):
        """Persona prose describing noble or title/race alone never implies social identity."""
        npc = MagicMock(spec=NPC)
        npc.race = "elf"
        npc.npc_title = "宮廷大貴族"
        npc.db.persona = {
            "identity": {"public": "世代傳承的尊貴大貴族"},
            "life_story": "出生於貴族之家，血統純正。",
        }
        npc.attributes.has.return_value = False
        # Reading social identity must be empty despite noble persona/title/elf race
        self.assertEqual(read_social_identities(npc), frozenset())

    @covers_requirement("social-identity::identity-writes-follow-deterministic-construction")
    def test_guild_registration_union_and_rollback(self):
        """Guild registration adds adventurer to existing identities, rolls back on error."""
        from world.rules.guild import _registration_snapshot, _restore_registration
        actor = MagicMock()
        stored = {"social_identities": ("noble",)}
        actor.attributes.has.side_effect = lambda k, **kw: k in stored
        actor.attributes.get.side_effect = lambda k, **kw: stored.get(k)
        actor.attributes.add.side_effect = lambda k, v, **kw: stored.update({k: v})
        actor.db = SimpleNamespace(social_identities=("noble",))
        staff = MagicMock()

        snapshot = _registration_snapshot(actor, staff)
        # Perform union
        set_social_identities(actor, read_social_identities(actor) | {"adventurer"})
        self.assertEqual(read_social_identities(actor), frozenset({"noble", "adventurer"}))

        # Restore rollback
        _restore_registration(actor, staff, snapshot)
        actor.attributes.get.side_effect = lambda k, **kw: stored.get(k)
        self.assertEqual(read_social_identities(actor), frozenset({"noble"}))
