## MODIFIED Requirements

### Requirement: Church venues and clergy hosts exist as authored content
Places whose authored kwargs carry the `church` flag SHALL form the derived church-place set in `world/lore/church/` (the `shop_key` derivation pattern), and the derivation SHALL fail closed on a duplicate-flagged authoring conflict. The `ChurchHost` typeclass component (sibling of `GuildStaff`, a zero-state capability adapter) SHALL be authored on the one registered clergy NPC roster row (艾莉安娜‧寒水 high celebrant) through her profession blueprint — per owner decision the sanctum steward 羅海西亞‧芬威克 stays a plain merchant selling the sanctum's wares and SHALL NOT carry the component nor the arousal seed — and that row SHALL carry the small raised-initial-arousal authoring kwarg on its spawn data. No gameplay mechanic consumes the venue set or the host at this stage — the enrollment and accrual changes do — but `place-driven-service-sync` convergence SHALL stay idempotent with the new component attached and the derived set SHALL be non-empty.

#### Scenario: The derived church set is complete and fail-closed
- **WHEN** the lore package derives the church-place set from authored kwargs
- **THEN** every `church`-flagged place appears exactly once, and a duplicate/conflicting church kwarg authoring raises at derivation instead of silently winning

#### Scenario: The clergy host is authored and sync-idempotent
- **WHEN** the profession-blueprint roster derivation and `place-driven-service-sync` converge with `ChurchHost` attached to the celebrant NPC
- **THEN** she resolves through the local-service-host lookup, her spawn data carries the raised initial arousal, the sanctum steward resolves as a plain merchant without the component, and a second sync pass changes nothing

### Requirement: Enrollment is a deterministic three-stage transaction behind a ChurchHost
`church join` (aliases 入教／洗禮) SHALL resolve a local `ChurchHost` component (sibling of `GuildStaff`, authored on the registered high celebrant 艾莉安娜‧寒水 only) through the existing local-service-host resolution, pass the schedule gate (`interaction_reason(host, "service_church")`), then run the deterministic `world/rules/church.py::enroll(caller, host)` — no dialogue-model call participates. Enrollment SHALL create the ledger, stamp `enrolled_tick`, and emit `church_enrolled` via the transaction-commit seam. Re-enrollment SHALL be a stable rejection (「你已屬光明教會」) with no writes. Missing host, off-duty host, and every other failure SHALL be a stable rejection message, and a rolled-back enrollment SHALL leave the character byte-identical with no event.

#### Scenario: A clean enrollment commits and logs once
- **WHEN** an unaffiliated player character completes `church join` beside an on-duty ChurchHost
- **THEN** the ledger exists, exactly one `church_enrolled` event is emitted at commit, and the whole flow works with every LLM service dead

#### Scenario: Re-enrollment changes nothing
- **WHEN** an already-enrolled character calls `church join` again
- **THEN** the stable rejection is returned and ledger, skills, and inventory are byte-identical with no event

#### Scenario: No host means no enrollment
- **WHEN** `church join` runs with no local ChurchHost, or the host's schedule gate declines
- **THEN** a stable rejection names the reason and no state is written
