"""CONCEPT placeholder / custom-draft journey value helpers.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; every body ships verbatim."""

from __future__ import annotations

from web.browser_support.browser_fixtures_data.mode import synth_mode_enabled

def concept_affinity_checked_testids(
    expected: tuple[str, ...], *, synth: bool | None = None
) -> tuple[str, ...]:
    """The affinity checkboxes the CONCEPT placeholder journey must find checked.

    The shipped proposal names two shipped elements, so the journey pins
    their exact checkbox testids (``creation-affinity-<element>``). The
    synthetic placeholder deliberately carries an EMPTY affinity — the
    closed element enum makes a shipped-name check meaningless, while the
    journey still proves the placeholder prefills the picker region (the
    checkboxes are rendered and nothing is checked) — so synthetic mode
    expects no checked box.
    """
    return () if (synth_mode_enabled() if synth is None else synth) else tuple(
        f"creation-affinity-{key}" for key in expected
    )


def concept_placeholder_values(panel: dict, *, synth: bool | None = None) -> dict:
    """The identity the CONCEPT placeholder journey must observe pre-filled.

    Re-derives, purely from the panel the server just presented (no Django
    settings needed — safe in the Playwright-side process), exactly what the
    browser-settings resolver proposes: shipped mode forwards the wizard's
    own snapshot values verbatim; synthetic mode derives the FIRST advertised
    race/subrace pair from the custom block and the greedy span-fill of the
    matching advertised profile (the same rule the server applies against
    the live profile), with the empty affinity the placeholder always carries.

    ``synth`` overrides the process default: a journey whose dedicated
    runtime boots the shipped catalogs (the creation journeys -- the
    creation panel's wire contract is fixed shipped schema vocabulary on
    both endpoints, including the shipped client validator) must forward
    the wizard's shipped snapshot even though the Playwright-side process
    itself runs with the harness's synthetic default.
    """
    proposal = panel["proposal"]
    synth_boot = synth_mode_enabled() if synth is None else synth
    if not synth_boot:
        return {
            "race": proposal["race"],
            "subrace": proposal["subrace"],
            "allocations": dict(proposal["allocations"]),
            "affinity_elements": list(proposal["affinity_elements"]),
            "affinity_checked": concept_affinity_checked_testids(
                proposal["affinity_elements"], synth=synth_boot
            ),
        }
    custom = panel["custom"]
    race = custom["races"][0]
    race_key = race["key"]
    subrace_key = (race["subraces"] or [None])[0]
    profile = next(
        p for p in custom["profiles"]
        if p["race"] == race_key and p["subrace"] == subrace_key
    )
    remaining = profile["budget"]
    allocations: dict[str, int] = {}
    for axis in profile["axes"]:
        value = min(axis["maximum"] - axis["minimum"], remaining)
        allocations[axis["axis"]] = value
        remaining -= value
    if remaining != 0:
        raise AssertionError("profile budget exceeds allocatable axis spans")
    return {
        "race": race_key,
        "subrace": subrace_key,
        "allocations": allocations,
        "affinity_elements": [],
        "affinity_checked": (),
    }
