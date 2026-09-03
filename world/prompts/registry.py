"""The code-defined prompt-key registry: files, placeholder allowlists, bounds.

``world/prompts/`` is a read-only registry package: the initial prompt text
ships in the top-level ``prompts/*.yaml`` data folder, and this module is the
code-side contract the loader validates every YAML file against. Each key
declares its file, the placeholder tokens it allows (wired to the concrete data
each caller passes), and a maximum text length, so admins edit only the ``text``
block while the loader still catches typos like ``{nmme}``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSpec:
    """The code-side contract for one prompt key.

    Attributes:
        key: The dotted ``file.domain`` key that consumers render.
        file: The ``*.yaml`` file under the prompt root that owns this key.
        allowed_placeholders: the ``{token}`` forms the loader permits in the
            text and ``render_prompt`` will substitute.
        max_length: the upper bound in characters on the prompt text.
    """

    key: str
    file: str
    allowed_placeholders: tuple[str, ...] = ()
    max_length: int = 4096


def _build() -> dict[str, PromptSpec]:
    """Build the keyed spec registry; one entry per layer or domain."""
    specs = (
        PromptSpec("narrator.system", "narrator.yaml"),
        PromptSpec("npc_dialogue.system", "npc_dialogue.yaml", ("name", "desc", "location", "persona")),
        PromptSpec("scenario_director.system", "scenario_director.yaml", ("name_inspiration",)),
        PromptSpec("npc.thinking", "npc.yaml", ("name",)),
        PromptSpec("art.style", "art.yaml"),
        PromptSpec(
            "art.character_description",
            "art.yaml",
            ("race", "name", "age", "style"),
        ),
        PromptSpec(
            "art.monster_description",
            "art.yaml",
            ("description", "display_name", "examples"),
        ),
        PromptSpec("art.scene_prompt", "art.yaml", ("description",)),
        PromptSpec("art.portrait_prompt", "art.yaml", ("description",)),
        PromptSpec("art.negative_prompt", "art.yaml"),
        PromptSpec(
            "character_creation.system",
            "character_creation.yaml",
            ("concept", "race_catalog"),
        ),
        PromptSpec(
            "scene_builder.system",
            "scene_builder.yaml",
            ("scene_sentence", "quest_context", "room_name", "region"),
        ),
        PromptSpec(
            "action_options.system",
            "action_options.yaml",
        ),
        PromptSpec(
            "action_options.user",
            "action_options.yaml",
            (
                "room_name",
                "room_summary",
                "npc_entries",
                "monster_entries",
                "objective",
                "narrative_tail",
                "affordances",
            ),
        ),
        PromptSpec("title_nomination.system", "title_nomination.yaml"),
        PromptSpec(
            "title_nomination.user",
            "title_nomination.yaml",
            ("player_name", "full_title", "recent_events", "declined", "removed"),
        ),
    )
    return {spec.key: spec for spec in specs}


PROMPT_SPECS: dict[str, PromptSpec] = _build()