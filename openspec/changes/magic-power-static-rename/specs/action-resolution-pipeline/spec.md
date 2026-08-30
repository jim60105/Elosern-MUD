## MODIFIED Requirements

### Requirement: Casting an elemental spell above the caster's tier without mastery is rejected
`ActionResolver.preflight` and `resolve` SHALL additionally reject a cast whose target skill is an
elemental spell when `can_cast_spell_tier(caster, element, tier)` returns `False`, using the same
rejection category already used for unowned-skill casts (no new `RejectReason` member).

#### Scenario: Preflight rejects an under-tier cast with no mastery
- **WHEN** `preflight` is called for a cast of a 賢者-tier fire spell by an entity with
  `magic_power.value == 20` and no owned `fire_mastery`
- **THEN** it returns the same rejection category as an unowned-skill cast

#### Scenario: An entity meeting the tier or holding mastery passes this check
- **WHEN** `preflight` is called for a cast of a 賢者-tier fire spell by an entity with either
  `magic_power.value >= 71` or owned `fire_mastery`
- **THEN** this check does not reject the cast (other unrelated checks still apply normally)

#### Scenario: A malformed elemental spell fails closed
- **WHEN** `preflight` is called for a cast of an elemental spell whose `mp` cost falls outside
  every §4.3 tier band (for example `mp == 5`) by an entity that would otherwise meet the gate
- **THEN** it is rejected with the same category as an unowned-skill cast (the malformed spell
  never passes ungated)

### Requirement: ActionResolver exposes shared side-effect-free action preview
The deterministic rules layer SHALL expose a frozen preview query factored from the same pure checks used by `ActionResolver.preflight()`. Given an actor, skill, context, and optional candidate, it SHALL report enabled state, the exact stable rejection reason and resource detail when disabled, and valid targets or applicable AREA shorthands. It SHALL cover ownership and active kind, current resources, exact target shape, presence, alive state, range, faction, action-blocking buffs, `actions_per_turn == 0`, registered effect prefixes, time metadata, and elemental spell-tier eligibility. The spell-tier check SHALL use the single shared side-effect-free predicate `world.rules.progression.can_cast_skill(entity, skill)` — the same predicate consumed by `ActionResolver` and the deterministic AI policies — so preview, submission revalidation, and authoritative preflight agree on the same eligibility; an over-tier spell SHALL report `RejectReason.UNKNOWN_SKILL` with the skill key, and a malformed elemental spell SHALL fail closed (disabled, never raising). The same checks SHALL apply to the combat-session submission revalidation path, so a rejected submission stops before initiative. Modifier evaluation SHALL read a no-create context from existing stored buff and sexual-state data and SHALL NOT materialize a lazy handler or default. Preview SHALL NOT roll randomness, stage or apply effects, construct EventLogs, invoke event-effect planners, mutate any persistent or nonpersistent game state, or advance world time. `preflight()` and final `resolve()` SHALL remain authoritative and SHALL rerun their required checks.

#### Scenario: Preview has no side effects
- **WHEN** previews are built for every owned active skill and every current combat participant
- **THEN** traits, resources, buffs, sexual state, battlefield state, session record, quest state, random source, EventLogs, and world clock are unchanged

#### Scenario: Preview reuses a named resolver rejection
- **WHEN** an active skill costs more MP than the actor currently has
- **THEN** preview reports disabled with `RejectReason.INSUFFICIENT_RESOURCE` and MP detail, matching preflight without executing an effect

#### Scenario: An over-tier owned spell is disabled in preview and revalidation
- **WHEN** an actor owns and can afford `firestorm` (術師 tier, 30 MP) at `magic_power == 15` with no declared affinities and no owned `fire_mastery`, so `floor(15 × 1.0) == 15` is below the 16 threshold
- **THEN** preview reports disabled with `RejectReason.UNKNOWN_SKILL` naming the skill key, submission revalidation reports the same, and `ActionResolver.preflight()` rejects with the same reason — the three agree

#### Scenario: The affinity boundary passes the preview gate
- **WHEN** the same actor additionally declares `affinity_elements == ["fire"]`, so `floor(15 × 1.1) == 16` meets the 術師 threshold — or holds `magic_power == 16` with no affinities, so `floor(16 × 1.0) == 16` meets it on the pure numeric path
- **THEN** preview and submission revalidation report the spell enabled (when other checks pass), exactly as preflight succeeds

#### Scenario: The mastery override enables a tier-blocked spell in preview
- **WHEN** the actor's `owned_keys()` contains `fire_mastery` regardless of magic level
- **THEN** preview and submission revalidation report the spell enabled, exactly as preflight succeeds

#### Scenario: A conferred mastery grant does not override the preview gate
- **WHEN** the actor's `db.skill_grants` contains a conferred `fire_mastery` grant but `owned_keys()` does not
- **THEN** the spell remains disabled with `RejectReason.UNKNOWN_SKILL`, because the shared predicate honors direct ownership only

#### Scenario: A malformed elemental spell fails closed in preview
- **WHEN** the underlying tier lookup raises `ValueError` (malformed MP cost or unknown element) for an otherwise owned active spell
- **THEN** preview and submission revalidation report the spell disabled with `RejectReason.UNKNOWN_SKILL` and never raise, matching the resolver's fail-closed rejection

#### Scenario: Zero-action state is authoritative before initiative
- **WHEN** deterministic combat modifiers set the player actor's `actions_per_turn` to zero
- **THEN** preview and player-session submission report `RejectReason.ACTION_FORBIDDEN` before initiative while `run_round()` retains its existing skip behavior for an NPC or a post-preflight state change

#### Scenario: Preview does not materialize sexual state
- **WHEN** an actor has a stored sexual baseline but no materialized sexual trait handler and combat preview is built
- **THEN** modifier matching is interpreted in memory and no sexual trait Attribute or default handler state is created

#### Scenario: Target previews use ordinary ordered validation
- **WHEN** candidate previews are requested for a SINGLE or AREA skill
- **THEN** candidate acceptance and rejection use the same presence, alive, range, and faction functions and ordering as final target resolution

#### Scenario: The shared combat view marks a tier-blocked spell disabled
- **WHEN** the combat view (`build_combat_view`) is built for an actor who owns an affordable over-tier spell
- **THEN** the spell's descriptor carries `enabled == False` and the `unknown_skill` reason code, so both the Telnet `combat actions` command and the WebClient combat panel render it unavailable
