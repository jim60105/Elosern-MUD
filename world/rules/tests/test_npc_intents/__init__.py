"""NPC intent tests (npc-intents): registry-driven intent application over
kit rows — exam, item transfer, relation adjustment, party invite, quest
offer, lore reveal, completion gating, acquisition rollback, and the applier
boundary battery.

Package split of the original flat module; each slice module groups the
shipped classes by intent family. The shared registry-isolation base and
fixtures live in ``_support`` (not a collected test module).
"""
