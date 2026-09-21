## 1. The blueprint

- [x] 1.1 Add a place-bound `scripted_dialogue` component to the `merchant` row in
  `world/rules/rulebook/professions.yaml`, and extend the header comment to record that a
  shopkeeper both trades and answers.
- [x] 1.2 Confirm no loader change is needed: blueprint coverage, assembly and the
  dialogue-resolution check are all generic over the blueprint. Record that this was checked.

## 2. The eight tables

- [x] 2.1 Author four capital tables in `world/lore/dialogue/altoria.py` — general store,
  forge, eatery, tailor. Each names `shop stock`, `buy` and `sell`, and answers about what
  that shop actually carries.
- [x] 2.2 Author four village tables in `world/lore/dialogue/ciaran.py` — blade-smith,
  flower-cook, collector, weaver. **Re-read the elven-village deep-dive before drafting.**
  These are villagers sharing what they make; none may speak as a proprietor, quote hours as
  policy, or call her goods stock.
- [x] 2.3 Add a `dialogue_key` to all eight place rows across the terrace slices and
  `places_ciaran.py`.
- [x] 2.4 Do not write one template and substitute nouns. The spec requires each host to
  answer about its own goods, and that is the assertion.

## 3. Coverage

- [x] 3.1 Talking to a merchant host returns its authored greeting and its keywords answer.
- [x] 3.2 A synthetic merchant place authoring no dialogue key fails load naming the place
  and the missing kwarg.
- [x] 3.3 Stock listing, buying and selling are unchanged — capture before and after.
- [x] 3.4 An existing merchant host gains the component by convergence on the next sync,
  without being deleted and recreated and without its authored name or title changing. The
  never-rename contract makes this the only acceptable path.
- [x] 3.5 The village hosts' authored dialogue contains no proprietor language — assert
  against the authored text, which is data this test may read directly.

## 4. Handoff

- [x] 4.1 Run the guild-config, guild-economy-sync, scripted-dialogue and shop-economy suites
  plus `uv run --locked python -m tools.spec_traceability check`.
