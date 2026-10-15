# Proposal: Defeated foes and downed allies stay on the stage with an unmistakable look

## Why

With the roster removed (`webclient-combat-formation`), the stage is the only place the player sees who is still in
the fight. The user ruled that knocked-out and defeated foes keep their slot and must read as "defeated" at a glance,
without relying on colour or brightness. That look must differ from the dialogue and target-step dims and from an
unconscious ally. Today a defeated foe fades out of the line-up.

## What Changes

- **Defeated foe** (`knocked_out` or `defeated`): the figure keeps its formation slot and shows:
  - a slump (8° away from the centre, lowered 6%);
  - `grayscale(1)` brightness 0.45 at 0.8 opacity, silhouette intact;
  - a CSS/SVG **broken-seal** mark over the chest;
  - plate text `✕ 已擊破` with an empty dashed stroke;
  - accessible name ending in 已擊破.
- **Downed ally** (`knocked_out` companion), the sibling treatment:
  - a kneel (lowered 8%, compressed to 92%, no rotation);
  - `grayscale(0.6)` brightness 0.7;
  - no seal;
  - plate text `▼ 倒地`.
- Both differ from the listener/target dim (colour, pose and opacity kept, no mark, no text) by shape and text.
- They work for a portrait, a placeholder silhouette and failed art (the treatment sits on the figure wrapper).
- **Motion:**
  - the defeat beat collapses the foe over `--motion-beat-defeat` on the exit easing, and the seal fades in after;
  - `reduced`: the pose applies without travel and the tone and mark fade within 150ms;
  - `off`, reload and reconnect: at rest.
- The formation counts every non-fled foe. A fled foe fades and the formation re-forms. A defeated foe never
  triggers a re-form.
- Stories cover a defeated portrait, placeholder and failed art, a full line-up with some defeated, a downed ally,
  and reduced/off, plus a side-by-side "fallen vs dim" story. Focused tests and one browser method are included.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-contextual-hud`:
  - adds "Fallen combat figures read as defeated or down at a glance";
  - amends "Combat figures stand in a shared-scale formation" (non-fled foes) and "Combat figures carry glance
    plates" (fallen plate state);
  - amends the beat choreography (defeat collapses and stays) and the visibility matrix's foe row.

## Impact

- Code (`web/webclient-app/`):
  - `components/StageActor.vue`: a `fallen` prop (`"defeated" | "down" | null`) with the treatment classes, the seal
    mark element and the transition hooks;
  - `components/FoeLineup.vue` and `components/CompanionLineup.vue`: pass `fallen` from the participant state;
  - `components/foe-lineup.js`: drawn set = non-fled foes;
  - `components/FigurePlate.vue`: the fallen readout;
  - `AppClient.vue`: participant state to the line-ups;
  - the beat queue's defeat handling (`lib/beat_queue.js`): keep the foe instead of removing it;
  - `styles/tokens.css`: a fallen-pose token set.
- Tests: Vitest for StageActor, the line-ups and the plate; one browser method registered in
  `.github/browser-shards.json`; migration of beat tests that expected the foe to leave.
- Stories: `Core/StageActor` and `Core/FoeLineup` fallen stories, `Core/AppShell` line-up stories.

## Batch: webclient combat stage

- depends-on: webclient-combat-formation
- depends-on: webclient-combat-figure-plates
- Code conflicts: `StageActor.vue`, `FoeLineup.vue`, `CompanionLineup.vue` and `FigurePlate.vue` with
  `webclient-combat-stage-target-picking`. It is the base for that change's MODIFIED blocks of the formation
  requirement.
