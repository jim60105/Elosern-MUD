"""
Exact exploration action payload validators and adapter tests.

Covers the six explore payload validators, the movement charge/recording
through the shared exit seam, the stale/tampered/locked rejections, the combat
plain traversal, the ``at_pre_move`` veto, scripted and free-form
dialogue (offline degrade included), engage-to-combat, and the shared skip
helper arithmetic.

Registry identities come from the synthetic kit: dialogue hosts answer from
the kit's lodgekeeper table (with the shipped guild-staff row merged through
a runtime probe for the production turnin special case), the guild-branch
component and delivery items are kit rows, and the practice suite drills a
kit skill inside a scoped registry.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level helpers live
in ``_support`` (not a collected test module).
"""
