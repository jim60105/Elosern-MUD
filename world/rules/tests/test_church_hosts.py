"""Data-contract test: the clergy host, ChurchHost service attachment, and spawn-data arousal

The one registered clergy roster row (艾莉安娜‧寒水 high celebrant) must
resolve as a live service host with the ChurchHost capability attached
through her direct capability declaration and the raised initial arousal
seeded into her spawn data; per owner decision the sanctum steward 羅海西亞‧
芬威克 stays a plain merchant — no ChurchHost, no arousal seed — while both
places keep the ``church`` venue flag the derived church-place set reads. Every other host
stays clear of the clergy component, and place-driven-service-sync
convergence is idempotent with the new component — a second pass changes
nothing, and a pre-change host is converged rather than duplicated.
"""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import ChurchHost, ScriptedDialogue
from typeclasses.npcs import NPC
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import sync_service_content
from world.rules.tests.test_guild_economy_sync._support import (
    ServiceContentIsolation,
    _merchant_row,
    canonical_host,
)

CELEBRANT_SERVICE_ID = "altoria_high_priestess"
STEWARD_SERVICE_ID = "altoria_sanctum_deacon"


def _church_place_rows():
    """The roster rows whose place is a church venue (the derived set projection)."""
    from world.lore.church.places import CHURCH_PLACES

    return {
        row.host_key: row
        for row in get_catalog().service_hosts
        if row.spawn_room in CHURCH_PLACES
    }


def _church_host_kwargs(row):
    """The authored church_host declaration kwargs of one roster row."""
    for declaration in row.components:
        if declaration.type == "church_host":
            return declaration.kwargs
    raise AssertionError(f"row {row.host_key!r} declares no church_host capability")


def _dialogue_key(row) -> str:
    for declaration in row.components:
        if declaration.type == "scripted_dialogue":
            return declaration.kwargs["dialogue_key"]
    raise AssertionError(f"row {row.host_key!r} declares no dialogue capability")


def _host_for(row):
    return NPC.objects.filter(db_key=row.name).first()


def _church_host(host):
    return host.components.get(ChurchHost.get_component_slot())


class ChurchHostSyncTests(ServiceContentIsolation, EvenniaTestCase):
    """Sync integration for the authored clergy host."""

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_the_celebrant_resolves_as_the_sole_church_host(self):
        sync_service_content()
        rows = _church_place_rows()
        # Both church places author the venue flag; only the celebrant row
        # carries the clergy capability.
        self.assertEqual(set(rows), {CELEBRANT_SERVICE_ID, STEWARD_SERVICE_ID})
        celebrant = _host_for(rows[CELEBRANT_SERVICE_ID])
        self.assertIsNotNone(celebrant)
        component = _church_host(celebrant)
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, CELEBRANT_SERVICE_ID)
        celebrant_row = rows[CELEBRANT_SERVICE_ID]
        self.assertEqual(component.church, _church_host_kwargs(celebrant_row)["church"])
        # Her spawn data carries the raised initial arousal authored on the
        # row (design §5.3), stored like any imported baseline.
        self.assertEqual(
            celebrant.db.sexual["arousal"],
            _church_host_kwargs(celebrant_row)["initial_arousal"],
        )
        # Place-bound anchoring is converged by the shared assembly.
        self.assertEqual(component.service_binding, "place")
        self.assertEqual(component.anchor_room_id, celebrant.location.pk)

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_the_steward_stays_a_plain_merchant_without_the_component(self):
        sync_service_content()
        steward_row = _church_place_rows()[STEWARD_SERVICE_ID]
        steward = _host_for(steward_row)
        self.assertIsNotNone(steward)
        # Owner decision: ministry is the celebrant's office alone — the
        # steward has no ChurchHost and no arousal seed, yet her merchant
        # surface (and the venue flag on the place) is intact.
        self.assertIsNone(_church_host(steward))
        self.assertIsNone(getattr(steward.db, "sexual", None))
        self.assertIsNotNone(
            steward.components.get(ScriptedDialogue.get_component_slot())
        )
        # Her declaration is the same merchant + dialogue pair the commercial
        # service host carries: the merchant surface is intact.
        self.assertEqual(
            [declaration.type for declaration in steward_row.components],
            [declaration.type for declaration in _merchant_row().components],
        )

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_no_other_host_carries_the_church_component(self):
        sync_service_content()
        for row in get_catalog().service_hosts:
            host = _host_for(row)
            if host is None:
                continue
            with self.subTest(host_key=row.host_key):
                if row.host_key != CELEBRANT_SERVICE_ID:
                    self.assertIsNone(_church_host(host))

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_a_second_sync_pass_changes_nothing(self):
        sync_service_content()
        before = {
            row.host_key: (_host_for(row).pk, dict(host.db.sexual or {}))
            for row in get_catalog().service_hosts
            if row.host_key in _church_place_rows()
            if (host := _host_for(row)) is not None
        }
        n_before = NPC.objects.all_family().count()
        sync_service_content()
        for service_id, (pk_before, sexual_before) in before.items():
            row = _church_place_rows()[service_id]
            host = _host_for(row)
            with self.subTest(service_id=service_id):
                self.assertEqual(host.pk, pk_before)
                self.assertEqual(dict(host.db.sexual or {}), sexual_before)
        self.assertEqual(NPC.objects.all_family().count(), n_before)

    @covers_requirement(
        "church-ordination::church-venues-and-clergy-hosts-exist-as-authored-content"
    )
    def test_a_pre_change_host_is_converged_not_duplicated(self):
        # A celebrant host synced before the ChurchHost declaration existed
        # (ScriptedDialogue only) must be REUSED: its canonical authored
        # identity is unchanged, so
        # convergence attaches church_host and seeds the authored arousal —
        # one host, never a second creation.
        rows = _church_place_rows()
        celebrant_row = rows[CELEBRANT_SERVICE_ID]
        room = search_object_by_tag(celebrant_row.spawn_room)[0]
        old = create_object(NPC, key=celebrant_row.name, location=room)
        old_dialogue = ScriptedDialogue.create(
            old,
            service_id=CELEBRANT_SERVICE_ID,
            dialogue_key=_dialogue_key(celebrant_row),
        )
        old.components.add(old_dialogue)
        canonical_host(old, celebrant_row)

        sync_service_content()

        converged = _host_for(celebrant_row)
        self.assertEqual(converged.pk, old.pk)
        self.assertEqual(NPC.objects.filter(db_key=celebrant_row.name).count(), 1)
        self.assertIsNotNone(_church_host(converged))
        self.assertEqual(
            converged.db.sexual["arousal"],
            _church_host_kwargs(celebrant_row)["initial_arousal"],
        )


if __name__ == "__main__":
    import unittest

    unittest.main()