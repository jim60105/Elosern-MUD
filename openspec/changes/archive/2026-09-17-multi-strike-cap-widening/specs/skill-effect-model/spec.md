## MODIFIED Requirements

### Requirement: A follow-up strike repeats damage on evidence or unconditionally without repeating the action
A validated damage policy SHALL permit up to two extra independent strikes — either against a target with matching recent evidence (the evidence-conditional shape: `repeat_when` naming a recognized evidence kind, pinned to exactly one extra strike) or unconditionally on every successful action resolution (the predicate-free shape: an extra-strike declaration of one or two with no `repeat_when`). Each strike SHALL have an independent hit roll and the same coefficient/policy. No strike's miss SHALL suppress any later strike. The action SHALL pay resources/time and award eligible practice once, project ordered damage correctly across every strike, and retain all rolls while emitting at most one terminal defeat or knockout for a target regardless of the declared count. The extra-strike count SHALL stay within the closed set {0, 1, 2} of ADDITIONAL strikes (total strikes = 1 + the declared count); every other shipped `DamagePolicy` validation SHALL stay fail-closed exactly as before — the unknown-evidence-kind rejection, the boolean-count rejection, and the 「`repeat_when` requires `extra_strikes` of exactly one」 pin included — and the construction rule 「an extra strike requires `repeat_when`」 SHALL stay retired so the predicate-free shape is legal vocabulary for any element.

#### Scenario: A first miss does not suppress the second roll
- **WHEN** fixed rolls make the first strike miss and the follow-up hit on an eligible target under an evidence-conditional policy
- **THEN** only the second damages HP and both rolls are recorded for one paid cast

#### Scenario: Ineligible target has one strike
- **WHEN** recent evidence is missing or expired for an evidence-conditional policy
- **THEN** only the ordinary strike occurs

#### Scenario: Repeated damage is atomic and nonlethal aware
- **WHEN** two strikes cross a protected target or a later commit step fails
- **THEN** successful settlement floors HP at 1 with one knockout; a failed settlement restores all HP and evidence

#### Scenario: An unconditional policy always resolves two independent strikes
- **WHEN** a synthetic damage policy declares its extra strike with no evidence predicate and strikes any living target under each fixed roll pair (hit-hit, miss-hit, hit-miss, miss-miss)
- **THEN** exactly two independent hit rolls are recorded and each landing strike deals the same coefficient/policy damage, whatever recent evidence the target does or does not hold, and a policy-free control skill on the same target still resolves exactly one strike

#### Scenario: The predicate-free shape is validated like every other policy
- **WHEN** policies declare an extra strike with a valid evidence kind, with no predicate, with an unknown evidence kind, with a boolean or out-of-cap strike count, or with `repeat_when` and a strike count other than one
- **THEN** the well-formed shapes construct (conditional and unconditional at each legal count), and each malformed combination — a boolean count, a count above the closed set, any count alongside an unknown evidence kind, or `repeat_when` with a count other than one — still raises at construction exactly as before the widening

#### Scenario: Two extra strikes resolve three independent rolls in one paid cast
- **WHEN** a synthetic unconditional policy declares two extra strikes against one living target under fixed rolls covering an all-hit sweep and a hit-miss-hit sweep
- **THEN** exactly three independent hit rolls are recorded in order, each landing strike deals the same coefficient/policy damage with ordered HP projection across the sweep, resources and practice move once, and per-strike diversion planning keeps honoring the shipped cap and gauge ledgers across all three strikes

#### Scenario: The terminal emission stays singular across the widest sweep
- **WHEN** three strikes together cross an unprotected target's lethal threshold, and separately cross a protected companion's floor under the nonlethal policy
- **THEN** the unprotected crossing produces at most one defeat credit for the cast and the protected crossing floors HP at 1 with exactly one knockout mark, no per-strike duplication of either terminal surface

#### Scenario: A three-strike sweep rolls back as one unit
- **WHEN** a later commit step fails midway through a three-strike settlement
- **THEN** every staged strike's HP movement, diversion spending, and evidence are restored to the pre-cast state
