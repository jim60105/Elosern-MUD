# internal-art-worker delta

## ADDED Requirements

### Requirement: Portrait prompts compose a full-body figure on a backdrop the cutout stage can key
`art.portrait_prompt` SHALL compose a FULL-BODY character illustration — the whole figure from head
to feet inside the frame — and SHALL NOT ask for a half-body, bust, or close-up crop. It SHALL ask
for a flat, uniform, light backdrop, carrying at minimum the `simple background` and
`white background` tags, and SHALL NOT ask for a painted, blurred, out-of-focus, textured, or
scenic background. `art.negative_prompt` SHALL carry the matching background and crop negatives so
the two templates cannot disagree.

This is a pipeline contract, not a taste preference: `art-portrait-cutout` runs its matting stage on
exactly the subject kinds `art.portrait_prompt` serves, and a painted or blurred backdrop is the
hardest input that stage can be handed. The constraint SHALL hold whether or not `ART_REMBG_ENABLED`
is set for a given deployment, so enabling the stage never requires a prompt edit and disabling it
never leaves a prompt that only made sense with the stage on.

`art.scene_prompt` SHALL be exempt: scene subjects are outside the cutout allowlist and SHALL keep
composing their painted foreground, midground, and background planes.

The generation model accepts natural-language English together with danbooru-style tags, so the
backdrop instruction MAY ride as trailing tags beside the prose rather than being spelled out as a
sentence. Both templates remain admin-tunable in the mounted `prompts/` folder; this requirement
constrains what the SHIPPED text composes, and an admin edit that violates it is the admin's
decision, surfaced through the existing rendered-prompt digest.

#### Scenario: The shipped portrait prompt asks for a full body on a flat backdrop
- **WHEN** the shipped `art.portrait_prompt` is rendered for a portrait subject
- **THEN** the positive prompt asks for a full-body figure with head and feet in frame, carries the `simple background` and `white background` tags, and asks for no painted, blurred, out-of-focus, or scenic backdrop

#### Scenario: The negative prompt agrees with the positive composition
- **WHEN** the shipped `art.negative_prompt` is rendered
- **THEN** it carries background negatives (detailed or scenic background, gradient background) and crop negatives (close-up, cropped legs or feet) consistent with the portrait composition

#### Scenario: Scenes keep their painted background
- **WHEN** the shipped `art.scene_prompt` is rendered for a scene subject
- **THEN** it still composes foreground, midground, and background planes and carries no white-backdrop instruction

#### Scenario: The composition does not depend on the cutout setting
- **WHEN** a portrait request is built with `ART_REMBG_ENABLED` true and again with it false
- **THEN** the rendered positive and negative prompts are byte-identical in both runs
