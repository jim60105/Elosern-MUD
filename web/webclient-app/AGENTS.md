# Webclient Design Direction

The webclient is being redesigned as an AVG (visual-novel) + RPG hybrid in which
artwork is a primary subject, not a MUD text column. Frame UI proposals and
changes accordingly, and ship them as OpenSpec changes (no standalone HTML
prototypes; the real app differs too much for a prototype to be useful).

- Target desktop 16:9 only.
- Layout: full-bleed stage on top; bottom band = message window (2/3 width) plus
  command panel (1/3, bottom-right). Keep the image area large; do not put a
  narrative column and minimap side by side eating ~60% of the width.
- The player's own generated portrait stands on stage at all times; NPCs and
  enemies stand opposite in dialogue and combat.
- Vitals (HP/MP/stamina) are hidden at full and auto-appear when damaged or under a
  condition; always shown in combat.
- Dialogue collapses the action dock, and pressing 交談 enters the dialogue screen
  immediately (the server has `greeting_for()` in `world/rules/dialogue.py` for a
  no-keyword opener).
- The command line is hidden by default and expands via `/` or an icon.
- The message window uses AVG click-to-advance paging with a typewriter effect,
  paged per action response and never breaking mid-sentence; the player may act
  while pages remain (leftover pages flush to the log).
- A motion layer covers scene/mode transitions, typewriter, and beat-by-beat combat
  choreography; structured combat beats in the server protocol are accepted.
- Minimap has no legend and a thin frame, the full map fits the view, the full log
  opens scrolled to the bottom, the dock has a fixed height, and redundant head
  cards, 美術展示, and quick-word chips are removed.

## Styling pitfall

`styles/app-shell.css` contains `.elosern-root …` rules that duplicate or override
component `<style>` blocks, and Storybook does not render under `.elosern-root`.
When restyling a component, grep app-shell.css for its class names and remove or
update the `.elosern-root` duplicates, and verify geometry with a live-client
browser test, not only Storybook.
