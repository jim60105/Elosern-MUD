""":module:`world.prompts` — the code-defined contract for every LLM prompt.

The top-level ``prompts/`` data folder is the sole source of prompt text; this
package is the read-only registry class (the same class as ``world/lore/``) that
maps each prompt key to its file, its placeholder allowlist, and its length
bound. Consumers must read keys through ``world.prompts.loader.render_prompt``
and never duplicate prompt text in Python.
"""

from world.prompts.registry import PROMPT_SPECS, PromptSpec
from world.prompts.loader import (
    PromptLibraryError,
    PromptUnavailableError,
    UnexpectedPromptValueError,
    UnknownPromptKeyError,
    load_prompt_library,
    prompt_library,
    render_prompt,
    reset_prompt_library,
)

__all__ = [
    "PROMPT_SPECS",
    "PromptLibraryError",
    "PromptSpec",
    "PromptUnavailableError",
    "UnexpectedPromptValueError",
    "UnknownPromptKeyError",
    "load_prompt_library",
    "prompt_library",
    "render_prompt",
    "reset_prompt_library",
]