"""Project-authored service components for guild-economy NPC hosts (D-1/D-9).

Components are capability markers and persistent service-data holders only.
They contain stable service/branch identifiers and the Merchant's persisted
stock state; every registration, quest, trade, examination, wallet, merit,
inventory, and rank mutation delegates to a deterministic-core API.
"""

from evennia.contrib.base_systems.components import Component, DBField


class GuildStaff(Component):
    """Capability marker and branch identity of one guild service host."""

    name = "guild_staff"
    service_id = DBField(default=None)
    branch_key = DBField(default=None)
    # Authored availability binding (service-anchoring D2): written by the
    # shared capability assembly from the declaration's own binding; only it
    # writes them.
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)


class ChurchHost(Component):
    """Capability marker of one clergy service host (sibling of GuildStaff).

    ``service_id`` is the authored roster anchor; ``church`` records the
    venue identity the place's ``church`` kwarg authors (the derived
    church-place set reads the place, this field records the same decision
    on the host as component identity); ``initial_arousal`` is the authored
    spawn-data seed the roster sync applies at host creation. The adapter
    holds no runtime state — enrollment and accrual read only its presence,
    ``service_id`` and the place-bound anchoring fields the shared assembly
    converges every sync.
    """

    name = "church_host"
    service_id = DBField(default=None)
    church = DBField(default=None)
    initial_arousal = DBField(default=None)
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)


class GuildExamReception(Component):
    """Capability marker and branch identity of one guild examination counter."""

    name = "guild_exam_reception"
    service_id = DBField(default=None)
    branch_key = DBField(default=None)
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)


class Merchant(Component):
    """Capability marker, shop identity, and persisted stock state of one merchant.

    ``merchant_stock`` maps offered item keys to the live finite stock quantity
    and ``last_restock_day`` records the last deterministic restock day. Both
    are service data; the economy APIs own every read and write.
    """

    name = "merchant"
    service_id = DBField(default=None)
    shop_key = DBField(default=None)
    merchant_stock = DBField(default=None)
    last_restock_day = DBField(default=None)
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)


class ScriptedDialogue(Component):
    """Capability marker and dialogue identity of one scripted dialogue host.

    Any NPC carrying this component answers authored ``talk`` lines from the
    immutable keyed table in ``world/rules/dialogue.py``.
    ``service_id`` is an optional authored anchor value: ordinary narrative
    dialogue declares only ``dialogue_key`` and no binding, while a
    place-associated table declares its own place binding.
    """

    name = "scripted_dialogue"
    service_id = DBField(default=None)
    dialogue_key = DBField(default=None)
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)


class QuestIssuer(Component):
    """Capability marker and issuer identity of one private-commission host.

    Carrying this component is the sole authored authority for issuing a
    private commission; a primary key alone would make every NPC a potential
    commissioner. ``issuer_key`` is the authored content key (``npc:<key>``
    form); an absent value resolves to the host's database identity
    (``npc:#<pk>``). ``service_id`` is the scoped identity a generated
    commission role carries. Identity only — every commission registration,
    mutation, and settlement delegates to the deterministic core.
    """

    name = "quest_issuer"
    service_id = DBField(default=None)
    issuer_key = DBField(default=None)
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)