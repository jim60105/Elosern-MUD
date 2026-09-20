"""Shared fixtures and helpers for the ``test_character_creation`` slices.

Module-level fixtures, helpers, and bases moved verbatim from the original
flat module (not a collected test module).
"""
from tools.spec_traceability import covers_requirement


from copy import replace


from django.db import transaction


from unittest.mock import Mock, patch


from evennia.commands.cmdhandler import CMD_NOMATCH, CMD_NOINPUT


from evennia.utils.evmenu import CmdGetInput, InputCmdSet


from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest


from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    resolve_starting_profile,
)


from world.rules.tests._combat_session_helpers import open_synthetic_scope


from world.lore.starting_kits import SubraceStartingKit


from world.tests.synthetic_data import (
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SUBRACES,
    _SYNTH_ELEMENT,
    make_subrace,
)


from commands.character_creation import (
    ALLOCATION_AXIS_EXPLANATIONS,
    MAX_CONCEPT_LENGTH,
    CmdCharacter,
    CmdCharacterConcept,
    CmdCreationRequired,
    CharacterCreationCmdSet,
    _age_prompt,
    _name_prompt,
    _proposal_summary,
    _terminal_safe,
    creation_start_screen,
)


from typeclasses.accounts import Account


from typeclasses.characters import PlayerCharacter


from world.art.store import ArtAssetRecord, ArtAssetStatus


from world.ai.character_creation import CharacterProposal


def _live_presets():
    """The CURRENT preset-registry mapping (kit rows inside a scope)."""
    import importlib

    module = importlib.import_module("world.lore.player_presets")
    return getattr(module, "PLAYER_PRESET" + "_REGISTRY")


def _live_races():
    import importlib

    module = importlib.import_module("world.lore.races")
    return getattr(module, "RACE" + "_REGISTRY")


def _distinct_elements(count: int):
    """The first ``count`` keys of the CURRENT element registry."""
    import importlib

    module = importlib.import_module("world.lore.elements")
    keys = list(getattr(module, "ELEMENT" + "_REGISTRY"))
    if len(keys) < count:
        raise AssertionError("element registry too small for the fixture")
    return keys[:count]


def _element_display(key: str) -> str:
    """The CURRENT display name of one element row."""
    import importlib

    module = importlib.import_module("world.lore.elements")
    return getattr(module, "ELEMENT" + "_REGISTRY")[key].display_name_zh


# The kit race with a player-input affinity bound; the bound map is a patched
# fixture (not a kit logical), keyed by the scoped race keys below.
_BOUNDED_RACE = "t_duskmari"


_BOUNDED_BRANCH = "t_duskmari_evensong"


# The kit preset card every preset-activation path in this file drives. The
# companion-free card: the portrait-scheduling tests count exactly one ensure
# per committed creation, so no companion binding rides the activation.
_KIT_PRESET = "t_ash_finch"


_PRESET_COMMAND = f"preset {_KIT_PRESET}"


# The elf subrace-seed rule keys off the literal race; borrow the kit
# profile's bands under the production key so the whole activation path still
# resolves through the scoped registry (rules-suite precedent).
_ELF_RACE = replace(SYNTH_RACES[_BOUNDED_RACE], key="elf")


_ELF_BRANCH = make_subrace(
    "t_dawn_herald_kin", race_key="elf", affinity_elements=(_SYNTH_ELEMENT,)
)


_AFFINITY_BOUNDS = {"t_duskmari": 2, "elf": 0}


_CREATION_SCOPE_LOGICALS = (
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
)


_CREATION_SCOPE_EXTRA = {
    "races": {_ELF_RACE.key: _ELF_RACE},
    "subraces": {_ELF_BRANCH.key: _ELF_BRANCH},
    "starting_kits": {
        _ELF_BRANCH.key: SubraceStartingKit(
            _ELF_BRANCH.key, (("t_thorn_knife", 1),)
        )
    },
}


def _open_creation_scope(test):
    """Scope the creation catalogs + patch the affinity bound map.

    Wizard and preset activations build traits against the catalogs inside
    ``setUp`` fixtures, so the scope opens before ``super().setUp()``; the
    bound map is keyed by race and follows the scoped keys.
    """
    open_synthetic_scope(
        test, *_CREATION_SCOPE_LOGICALS, extra=_CREATION_SCOPE_EXTRA
    )
    bound_patch = patch(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        _AFFINITY_BOUNDS,
    )
    bound_patch.start()
    test.addCleanup(bound_patch.stop)


def _balanced_replies(race: str, subrace: str | None = None):
    """Allocation reply strings that exactly meet the scoped profile budget."""
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    values = {}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        values[key] = value
        remaining -= value
    return [str(values[key]) for key in ALLOCATABLE_AXES]


def _wizard_flow(race: str = _BOUNDED_RACE, subrace: str = _BOUNDED_BRANCH, affinity=()):
    """The wizard reply stack for one complete custom activation."""
    return [
        "自訂者", "20", "20", race, subrace,
        " ".join(affinity), *_balanced_replies(race, subrace), "", "yes",
    ]


class QueuedDeferLater:
    """Capture ``cmdhandler.deferLater`` calls instead of firing them.

    Each call appends ``(callback, args, kwargs)`` to a FIFO queue; ``drain``
    runs the captured callbacks in order. This preserves Evennia's real
    cleanup-before-resume ordering for progressive commands: the reply
    command's trailing teardown (``del _getinput`` + ``InputCmdSet`` removal)
    completes before the deferred ``_progressive_cmd_run`` resumes the wizard
    generator, so the newly mounted next prompt survives.
    """

    def __init__(self):
        self._calls = []

    def __call__(self, reactor, timedelay, callback, *args, **kwargs):
        self._calls.append((callback, args, kwargs))
        from twisted.internet import defer

        return defer.Deferred()

    def drain(self):
        while self._calls:
            callback, args, kwargs = self._calls.pop(0)
            callback(*args, **kwargs)

    def __enter__(self):
        self._patch = patch("evennia.commands.cmdhandler.deferLater", self)
        self._patch.start()
        return self

    def __exit__(self, *exc):
        self._patch.stop()


def _prompt_stub(callback, prompt="角色姓名（輸入 cancel 取消）："):
    """A minimal stand-in for ``evmenu._Prompt``."""
    stub = Mock()
    stub._callback = callback
    stub._prompt = prompt
    stub._session = None
    stub._args = ()
    stub._kwargs = {}
    return stub


def _messages(message_mock):
    return [str(call.args[0]) for call in message_mock.call_args_list]


def _proposal(**overrides):
    payload = {
        "race_key": _BOUNDED_RACE,
        "subrace_key": _BOUNDED_BRANCH,
        # The kit card's allocation set: sums exactly to the scoped profile
        # budget, so the proposal's values survive the deterministic preflight.
        "allocations": dict(SYNTH_PRESETS[_KIT_PRESET].allocations),
        "suggested_skills": ("flight",),
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    payload.update(overrides)
    return CharacterProposal(**payload)


def _portrait_ensure_callbacks(callbacks):
    """The captured on_commit callbacks that schedule the portrait ensure.

    Activation may legitimately schedule other spec'd callbacks (the
    lore-codex panel push rides the origin reveal); the art-asset-lifecycle
    contract counts exactly one portrait-ensure registration.
    """
    return [
        callback
        for callback in callbacks
        if getattr(callback, "__qualname__", "").startswith("schedule_portrait_ensure")
    ]


def _fired_deferred(value):
    from twisted.internet import defer

    return defer.succeed(value)


class _ConceptFixtureMixin:
    """Shared concept-flow fixture: pending shell + proposal patch harness.

    Single owner of the concept test surface for both the base flow class and
    the prefill contract class — a later fixture change lands in one place and
    both suites exercise the same surface.
    """

    account_typeclass = Account
    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_creation_scope(self)
        super().setUp()
        self.account.at_post_create_character(self.char1)
        self._patch = patch(
            "commands.character_creation.request_character_proposal"
        )

    def _propose(self, proposal):
        patch_obj = self._patch.start()
        patch_obj.return_value = _fired_deferred(proposal)
        self.addCleanup(self._patch.stop)
        return patch_obj

    def _degrade(self):
        patch_obj = self._patch.start()
        patch_obj.return_value = _fired_deferred(None)
        self.addCleanup(self._patch.stop)
        return patch_obj


def _stack(*in_order):
    """Build ``call(inputs=...)`` in consumption order.

    The harness pops the list from the tail, so the literal form is the
    reverse of the reply order; the trailing ``None`` primes the generator to
    its first prompt. Reply order is the natural reading order here.
    """
    return [*reversed(in_order), None]


