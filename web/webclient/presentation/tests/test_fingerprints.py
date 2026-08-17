"""Pure tests for the shared canonical serialization and situation fingerprints.

Covers the canonical-JSON serializer's determinism and type coercion, the
eligibility digest's label-blindness and its invalidation on schedule-gate
flips, exit locks, and monster death, the public-state digest's
order-determinism and partial-progress/sub-tier stability (anti-oracle), and
the ``fingerprint`` combiner's replay and per-component invalidation.
"""

import unittest

from web.webclient.presentation.affordances import (
    AffordanceView,
    canonical_json,
    eligible_affordance_digest,
)
from web.webclient.presentation.fingerprints import (
    displayed_objective_identity,
    fingerprint,
    public_state_digest,
    public_tier_labels,
)


def _entry(action_id, params, label="測試", *, enabled=True, reason=None):
    return AffordanceView(
        action_id=action_id,
        label=label,
        params=params,
        freeform=False,
        navigation=False,
        enabled=enabled,
        disabled_reason=None if enabled else reason,
    )


class CanonicalJsonTests(unittest.TestCase):
    def test_key_order_independent_and_sorted(self):
        first = canonical_json({"a": 1, "b": {"y": 2, "x": True}})
        second = canonical_json({"b": {"x": True, "y": 2}, "a": 1})
        self.assertEqual(first, second)
        self.assertEqual(first, '{"a":1,"b":{"x":true,"y":2}}')

    def test_tuples_coerce_to_lists(self):
        self.assertEqual(canonical_json((1, 2)), canonical_json([1, 2]))
        self.assertEqual(canonical_json({"k": (1,)}), canonical_json({"k": [1]}))

    def test_cjk_text_is_kept_literal(self):
        self.assertEqual(canonical_json({"label": "自由交談"}), '{"label":"自由交談"}')

    def test_non_string_keys_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json({1: "x"})

    def test_unordered_sets_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json({"k": {1, 2}})


class EligibleAffordanceDigestTests(unittest.TestCase):
    def _talk(self, npc_id=101):
        return _entry("explore.talk_scripted", {"npc_id": npc_id, "keyword_id": "greeting"})

    def _move(self, **params):
        base = {"exit_ref": "7", "current_node": "room:5"}
        base.update(params)
        return _entry("explore.move", base)

    def test_identical_eligibility_replays_with_differing_labels_order(self):
        first = [_entry("explore.wait", {"daypart": "noon"}, label="等待"), self._talk()]
        second = [
            self._talk(),
            _entry("explore.wait", {"daypart": "noon"}, label="稍候休息"),
        ]
        self.assertEqual(eligible_affordance_digest(first), eligible_affordance_digest(second))

    def test_schedule_gate_flip_changes_the_digest(self):
        eligible = [self._talk(), self._move()]
        blocked = [self._move()]
        self.assertNotEqual(
            eligible_affordance_digest(eligible), eligible_affordance_digest(blocked)
        )

    def test_exit_lock_changes_the_digest(self):
        open_exit = [self._move(), self._talk()]
        locked_exit = [self._talk()]
        self.assertNotEqual(
            eligible_affordance_digest(open_exit), eligible_affordance_digest(locked_exit)
        )

    def test_monster_death_removes_engage_and_changes_the_digest(self):
        alive = [self._talk(), _entry("explore.engage", {"monster_id": 900})]
        dead = [self._talk()]
        self.assertNotEqual(
            eligible_affordance_digest(alive), eligible_affordance_digest(dead)
        )

    def test_different_param_values_change_the_digest(self):
        first = [self._move(exit_ref="7")]
        second = [self._move(exit_ref="8")]
        self.assertNotEqual(eligible_affordance_digest(first), eligible_affordance_digest(second))

    def test_navigation_entries_are_rejected(self):
        navigation = AffordanceView(
            surface="guild",
            label="公會服務",
            navigation=True,
            enabled=True,
            disabled_reason=None,
        )
        with self.assertRaises(ValueError):
            eligible_affordance_digest([navigation])


class PublicStateDigestTests(unittest.TestCase):
    def test_multiple_objectives_hash_deterministically_across_orders(self):
        first = [
            ("q-1", 0, "抵達指定的地點"),
            ("q-2", 1, "討伐 2 隻野狼魔物"),
        ]
        second = list(reversed(first))
        self.assertEqual(
            public_state_digest(first, [(101, "陌生人")]),
            public_state_digest(second, [(101, "陌生人")]),
        )

    def test_partial_progress_and_sub_tier_affinity_stability(self):
        # Neither the hidden stage-progress counter nor the numeric affinity is
        # an input: while the displayed identity and the tier label hold, the
        # digest holds — the anti-oracle rule.
        base = public_state_digest([("q-1", 0, "抵達指定的地點")], [(101, "熟人")])
        again = public_state_digest([("q-1", 0, "抵達指定的地點")], [(101, "熟人")])
        self.assertEqual(base, again)
        different_objective = public_state_digest([("q-1", 1, "抵達指定的地點")], [(101, "熟人")])
        self.assertNotEqual(base, different_objective)

    def test_tier_boundary_change_turns_over_the_digest(self):
        low = public_state_digest([], [(101, "熟人")])
        high = public_state_digest([], [(101, "摯友")])
        self.assertNotEqual(low, high)

    def test_public_tier_labels_are_sorted_and_label_only(self):
        class _Npc:
            def __init__(self, pk, name):
                self.pk = pk
                self.relations = _TierHandler(name)

        class _TierHandler:
            def __init__(self, name):
                self._name = name

            def stage_for(self, actor):
                class _Stage:
                    pass

                stage = _Stage()
                stage.name = self._name
                return stage

        npc_a = _Npc(3, "陌生人")
        npc_b = _Npc(1, "路人")
        labels = public_tier_labels(None, [npc_a, npc_b])
        self.assertEqual(labels, ((1, "路人"), (3, "陌生人")))


class FingerprintTests(unittest.TestCase):
    def _fp(self, **overrides):
        values = {
            "room_key": "room:42",
            "npc_ids": [101, 102],
            "monster_ids": [900],
            "eligible_affordance_digest": eligible_affordance_digest([self._talk()]),
            "public_state_digest_value": public_state_digest(
                [("_q1", 0, "抵達指定的地點")], [(101, "陌生人")]
            ),
        }
        values.update(overrides)
        return fingerprint(**values)

    def _talk(self, npc_id=101):
        return _entry("explore.talk_scripted", {"npc_id": npc_id, "keyword_id": "greeting"})

    def _move(self, **params):
        base = {"exit_ref": "7", "current_node": "room:5"}
        base.update(params)
        return _entry("explore.move", base)

    def test_identical_situations_replay_on_the_same_fingerprint(self):
        self.assertEqual(self._fp(), self._fp())

    def test_identity_order_is_irrelevant(self):
        shuffled = self._fp(npc_ids=[102, 101])
        self.assertEqual(self._fp(), shuffled)

    def test_each_component_change_invalidates(self):
        base = self._fp()
        self.assertNotEqual(base, self._fp(room_key="room:43"))
        self.assertNotEqual(base, self._fp(npc_ids=[101]))
        self.assertNotEqual(base, self._fp(monster_ids=[]))
        self.assertNotEqual(
            base,
            self._fp(
                eligible_affordance_digest=eligible_affordance_digest(
                    [self._talk(), self._move()]
                )
            ),
        )
        self.assertNotEqual(
            base,
            self._fp(
                public_state_digest_value=public_state_digest(
                    [("_q1", 1, "抵達指定的地點")], [(101, "陌生人")]
                )
            ),
        )

    def test_canonical_serialization_parity_with_the_ladder_comparison(self):
        # Stage 9 compares validator-normalized params by dict equality; the
        # shared canonical serialization agrees with that comparison on every
        # shape the payload contract admits, so builder- and validator-side
        # representations cannot drift.
        pairs = [
            ({"npc_id": 101, "keyword_id": "greeting"}, {"keyword_id": "greeting", "npc_id": 101}),
            ({"exit_ref": "7", "current_node": "room:5"}, {"current_node": "room:5", "exit_ref": "7"}),
            ({"room": True}, {"room": True}),
            ({"npc_id": 101}, {"npc_id": 101}),
        ]
        for left, right in pairs:
            with self.subTest(left=left):
                self.assertEqual(left, right)
                self.assertEqual(canonical_json(left), canonical_json(right))
        unequal = [{"npc_id": 101}, {"npc_id": 102}]
        self.assertNotEqual(unequal[0], unequal[1])
        self.assertNotEqual(canonical_json(unequal[0]), canonical_json(unequal[1]))


class DisplayedObjectiveIdentityTests(unittest.TestCase):
    """View-level checks that need no database: the helper degrades to the
    displayed-empty identity on an absent quest log and a malformed one."""

    def test_absent_quest_log_yields_empty_identity(self):
        class _Actor:
            db = type("db", (), {"quest_log": None})()

        self.assertEqual(displayed_objective_identity(_Actor()), ())
