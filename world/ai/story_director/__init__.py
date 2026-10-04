"""StoryDirector layer: validated, value-only beat-proposal generation (design §7).

The generative half of the story-director boundary. It reads a bounded
candidate/request context, runs the shared guardrail, and returns at most one
:class:`BeatProposal` or no content. It never mutates game state and never
imports a deterministic owner: the narrative core decides routing, validation,
and scheduling.
"""

from __future__ import annotations

from world.ai.story_director.generation import (
    StoryDirectorClientRequiredError,
    StoryDirectorNotRegisteredError,
    build_generation_descriptor,
    generate_beat_proposal,
    register_story_director,
)
from world.ai.story_director.prompt import render_director_frame
from world.ai.story_director.proposals import (
    BEAT_KIND_CLUE,
    BEAT_KIND_FOLLOW_UP,
    BEAT_KIND_INVITATION,
    BEAT_KIND_LETTER,
    BEAT_KIND_QUEST_SEED,
    BEAT_KINDS,
    BeatProposal,
)
from world.ai.story_director.validators import STORY_DIRECTOR_OUTPUT_SCHEMA

__all__ = [
    "BEAT_KINDS",
    "BEAT_KIND_CLUE",
    "BEAT_KIND_FOLLOW_UP",
    "BEAT_KIND_INVITATION",
    "BEAT_KIND_LETTER",
    "BEAT_KIND_QUEST_SEED",
    "BeatProposal",
    "STORY_DIRECTOR_OUTPUT_SCHEMA",
    "StoryDirectorClientRequiredError",
    "StoryDirectorNotRegisteredError",
    "build_generation_descriptor",
    "generate_beat_proposal",
    "register_story_director",
    "render_director_frame",
]
