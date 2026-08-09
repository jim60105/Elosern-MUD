# WebClient Service and Character-Creation UI — Focused Design

**Date:** 2026-08-02
**Status:** Approved as part of the Browser-First MUD WebClient Suite
**Parent:** `2026-08-02-webclient-ui-design.md`
**Delivery units:** `webclient-service-menus`, `webclient-character-creation-ui`
**Depends on:** `webclient-oob-foundation`, existing guild/economy/quest/creation/onboarding APIs

---

## 1. Intent

This design makes finite service workflows discoverable without replacing their existing deterministic
transactions. Guild registration, quest decisions, shop quantities, inventory inspection, and character
creation become explicit panels and forms. Every action still resolves local service hosts, rank, state,
stock, balance, ownership, and the adult gate on the server.

Service menus and creation UI are separate delivery units because they run in different player modes and
depend on different domain contracts. They share foundation form, focus, revision, and dispatcher rules.

---

## 2. Goals and Non-Goals

### Goals

- Cover all existing guild, quest-board, quest-log, reward, examination, shop, wallet, and inventory
  command capabilities through finite controls.
- Show disabled actions with domain-derived reasons before submission when possible.
- Use bounded integer quantity fields while keeping copper arithmetic server-authoritative.
- Give pending characters a graphical preset/custom creation flow.
- Keep free-form names as text fields.
- Preserve all-or-nothing activation and the permanent adult rejection.
- Update affected panels together after every committed service action.

### Non-Goals

- No new quest, guild, shop, item-use, equipment-effect, or character-build mechanics.
- No remote service access.
- No client-side price, reward, rank, merit, stock, or trait allocation authority.
- No replacement account authentication system.
- No mobile forms.
- No single very long first-day browser gate; each service and creation panel has independent acceptance.

---

## 3. Shared Service Panel Contract

Every service panel payload contains:

- panel schema version and service kind;
- resolved local host identity and display name when a host is required;
- current player summary relevant to the service;
- rows with stable keys, localized labels, read-only details, and allowed action descriptors;
- stable unavailable reason for closed, ambiguous, unregistered, insufficient, ineligible, stale, or
  malformed conditions;
- pagination metadata for bounded lists;
- no live object references and no local filesystem paths.

Presenters resolve the service using the same local-host rules as commands. Zero or multiple eligible
hosts produce an unavailable panel; the browser cannot select a global merchant or examiner dbref.

> **Amended 2026-08-09 (change `webclient-service-menus`).** Host ambiguity degrades **per surface**
> rather than the whole panel: the `services` panel carries three nullable surfaces (`guild` /
> `shop` / `inventory`), and a surface with zero or multiple eligible hosts is `null` with a stable
> reason (`no_local_service_host` / `ambiguous_service_host`) while the other surfaces keep
> rendering (service-menus D1). The "no global merchant/examiner dbref" rule is unchanged.

---

## 4. Guild UI

### 4.1 Registration

An unregistered player in a valid guild hall receives branch display information and Register. The action
calls the existing registration API. It does not submit displayed traits or desired rank. The server
captures its own historical displayed-trait snapshot and always starts the player at F.

Already registered, wrong-branch, no-host, ambiguous-host, and active-operation cases show stable status
rather than a second registration action.

### 4.2 Quest board

The board lists offers eligible for the player's canonical guild rank. Selecting one opens the current
quest detail renderer rather than reconstructing prose in JavaScript. The detail panel supplies a stable
definition key and Accept descriptor when legal.

Acceptance re-resolves the local guild host/branch and current offer. A stale or removed offer is rejected
without creating a quest record.

### 4.3 Quest log

The log lists active/completed/failed/abandoned records in deterministic order and opens structured or
server-rendered detail. Legal actions can include Abandon and Turn In. Turn-in visibility is a preview;
reward identity, completion, branch, inventory capacity, wallet, merit, ACQUIRE progress, and exactly-once
claim remain one domain transaction.

### 4.4 Merit and examination

The rank panel shows current rank, cumulative merit, next threshold, and examination eligibility. Start
Exam appears only with one valid local examiner, exact next rank, sufficient merit, and no active
combat/exam. Dispatch calls `start_guild_exam()` and transitions the shell to the ordinary combat UI.
The UI cannot choose examiner stats, nonlethal policy, or target rank outside the next-rank descriptor.

---

## 5. Shop and Inventory UI

### 5.1 Shop stock

Each row contains item key, localized name, exact unit buy/sell copper, current/max stock as allowed by
the view, and Buy descriptor. Shop open state comes from the world clock. The browser displays a
server-provided total preview for a selected quantity, but the submitted payload contains item key and
quantity only.

### 5.2 Quantity control

Quantity is a decimal integer field with server-advertised minimum and bounded maximum. Spinner buttons
and keyboard arrows are convenience controls. Empty, non-integer, boolean-like, negative, zero, overly
large, or extra-field payloads are rejected before domain dispatch. The economy API repeats positive
quantity, funds, stock, price, and stock-cap checks.

### 5.3 Buying and selling

Buy calls the existing atomic operation that changes wallet, inventory, stock, and ACQUIRE progress.
Sell lists only inventory keys accepted by the current merchant and calls the corresponding atomic
operation. A stale unit price or stock revision does not authorize the previewed transaction; domain
state at commit is authoritative and the returned snapshot displays the result.

### 5.4 Inventory

Inventory preserves repeated item keys and displays aggregate quantities only as presentation. Expanded
details show equipped state and known definition data. Use, consume, and equip controls appear only
after an owning deterministic API and OpenSpec requirement exist. This UI suite does not make repeated
keys independently addressable without a domain identity model.

---

## 6. Service Action IDs

| Action ID | Payload | Domain API |
|---|---|---|
| `guild.register` | local service revision/guard only | existing registration operation |
| `guild.quest_accept` | definition key | existing guild acceptance operation |
| `guild.quest_abandon` | deterministic quest ID | quest abandon API |
| `guild.quest_turnin` | deterministic quest ID | atomic reward claim |
| `guild.exam_start` | exact next-rank key | `start_guild_exam` |
| `shop.buy` | item key, positive bounded quantity | atomic `buy` |
| `shop.sell` | item key, positive bounded quantity | atomic `sell` |

Read-only panel selection and detail navigation need no server mutation action. No generic `guild.command`
or `shop.command` accepts arbitrary command text.

---

## 7. Character-Creation Mode

### 7.1 Entry and state

An account puppeting a character with `creation_pending=True` receives `mode="creation"`. Normal
exploration and service mutation panels are absent. The creation presenter reads the existing wizard
state and immutable player preset/race registries.

The browser can reconnect at any saved wizard stage. The server remains the owner of step order and
accepted values; hidden or skipped client controls cannot activate an incomplete character.

### 7.2 Preset flow

Preset cards show key, race, allocation emphasis, one-line background, and allowed preview data. Choosing
a preset submits the stable preset key. Confirmation calls the existing creation path and activation
service. The browser does not submit calculated stats.

### 7.3 Custom flow

Finite controls include race, available allocation choices, and every registry-backed option already
supported by the custom wizard. Text fields include name and truly free-form supported values. Numeric
adult fields use bounded integer inputs but are still server validated.

The exact form is derived from current creation requirements. The UI does not expose persona/import-only
fields merely because they exist on a character card schema.

### 7.4 Adult gate

Client constraints communicate that both age values must be at least 18. The submission adapter rejects
missing, malformed, `age < 18`, or `apparent_age < 18` values through the existing deterministic creation
service. The browser cannot hide an age field, alter HTML constraints, or call activation directly to
bypass the gate.

### 7.5 Activation transition

Successful activation remains all-or-nothing for character state. The existing best-effort relocation to
the South Gate and onboarding arrival behavior remain unchanged. After activation and puppet refresh,
the server sends a full `exploration` snapshot. Relocation failure preserves activated state and returns
the existing explanatory degradation rather than reopening creation with a partially mutated character.

---

## 8. Form and Focus Behavior

- Arrow keys navigate finite lists and buttons.
- Tab and Shift+Tab navigate actual text/numeric fields within a form.
- Enter activates the focused control; form submission requires all server-declared required fields.
- Escape returns one panel level and does not discard saved server wizard state.
- Destructive Abandon, Forfeit, and final custom reset actions require a confirmation panel.
- Validation messages are associated with fields and announced through an accessible live region.
- A stale revision preserves typed unsent values locally where safe, refreshes server choices, and asks
  the player to review rather than automatically resubmitting.

No canonical service or creation state is stored in localStorage.

---

## 9. Error Handling

- Service host disappears or becomes ambiguous: perform no mutation, close action controls, and return a
  current local-service snapshot.
- Shop closes between render and submit: reject with current hours and unchanged balances/stock.
- Quest state changes between list and turn-in: reject or return existing idempotent claim result; never
  pay twice.
- Transaction exception: preserve existing rollback/cache restoration behavior and refresh all affected
  panels from canonical state.
- Unknown item/quest/rank/preset key: reject as malformed/tampered input with no partial writes.
- Creation presenter failure: retain text command wizard access and do not activate.
- Disconnect after submit: do not retry. Reconnect shows current wallet, inventory, quest, rank, or
  creation stage.

---

## 10. Tests and Acceptance

### Guild/quest

- Registration success and every existing rejection reason.
- Board list → detail → accept using keyboard only.
- Active detail → abandon and completed detail → turn in.
- Exactly-once reward under duplicate request and stale browser state.
- Merit/exam eligibility and transition into combat mode.
- No remote or ambiguous host access.

### Shop/inventory

- Open/closed status at fixed world times.
- Buy/sell quantity validation, exact copper, stock, cap, inventory, and ACQUIRE progress.
- Stale stock/price rejection and transaction fault rollback.
- Repeated item display does not alter persisted repeated-key semantics.
- No use/equip action appears without an owning API.

### Character creation

- Preset selection, confirmation, activation, and exploration snapshot.
- Custom finite controls and free-text field focus.
- Reconnect at each saved stage.
- Server rejection of both underage fields despite bypassed client validation.
- Failed activation transaction leaves pending state; failed post-activation relocation leaves activated
  state and reports degradation.

### Browser

Each panel has an independent keyboard-only success and rejection journey at both supported desktop
viewports. A short shell smoke test transitions creation → exploration → guild display → shop display,
but it is not the substitute for the independent transactional tests above.
