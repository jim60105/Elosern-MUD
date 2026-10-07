"""Synthetic owner fixtures shared by the S6 focused integration suites."""
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.tests.synthetic_data import synthetic_registries
from world.rules.clock import get_world_clock


class ConsoleOwnerTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        scope = synthetic_registries('races','subraces','monster_tiers','monster_species','monster_variants','items','quest_definitions','quest_issuances','guild_ranks')
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.player = create_object('typeclasses.characters.PlayerCharacter',key='t_console_player',location=self.room1)
        self.player.race = 't_duskmari'
        self.player.apply_race_baseline()
        self.player.db.inventory = []
        self.player.db.equipment = {}
        self.player.db.wallet = 0
        self.player.db.quest_log = []
        self.monster = create_object('typeclasses.monsters.Monster',key='t_console_monster',location=self.room1)
        self.monster.threat_tier = 't_faint'
        self.monster.apply_monster_tier()
        self.npc = create_object('typeclasses.npcs.NPC',key='t_console_npc',location=self.room1)
        self.target = f'#{self.player.pk}'
        self.clock = get_world_clock()

    def assert_refusal(self, code, call):
        from server.console.errors import ConsoleError
        with self.assertRaises(ConsoleError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)
