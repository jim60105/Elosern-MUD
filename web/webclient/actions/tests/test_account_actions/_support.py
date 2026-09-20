"""Shared module-level helpers for the ``test_account_actions`` test package."""


from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import unittest

from twisted.internet.task import Clock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from web.webclient.actions.account_actions import (
    ALREADY_CURRENT_CODE,
    ALREADY_CURRENT_MESSAGE,
    AFFECTED_PANELS,
    AccountActionError,
    CHARACTER_SLOTS_FULL_CODE,
    CHARACTER_SLOTS_FULL_MESSAGE,
    CREATE_FAILED_MESSAGE,
    CREATE_IN_COMBAT_MESSAGE,
    CREATE_SUCCESS_CODE,
    CREATE_SUCCESS_MESSAGE,
    IN_COMBAT_CODE,
    IN_COMBAT_MESSAGE,
    INVALID_CHARACTER_CODE,
    INVALID_CHARACTER_MESSAGE,
    NO_ACTIVE_SESSION_CODE,
    NO_ACTIVE_SESSION_MESSAGE,
    RECOVERY_FAILED_MESSAGE,
    RECOVERY_RESTORED_TEMPLATE,
    RECOVERY_RETAINED_TEMPLATE,
    SUCCESS_CODE,
    SUCCESS_MESSAGE,
    TRANSITION_PENDING_CODE,
    TRANSITION_PENDING_MESSAGE,
    _account_character_create_adapter,
    _account_character_switch_adapter,
    _attach_puppet,
    _perform_create,
    _perform_switch,
    _clear_transition_pending,
    _recover_transition,
    _transition_pending,
    set_clock_for_testing,
    validate_account_character_create_payload,
    validate_account_character_switch_payload,
)
from web.webclient.actions.dispatcher import (
    NO_PUPPET_CODE,
    handle_ui_action,
    retire_sequence,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import (
    FrozenCard,
    OptionsSnapshot,
    ProposalSnapshot,
    synchronize_session,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
