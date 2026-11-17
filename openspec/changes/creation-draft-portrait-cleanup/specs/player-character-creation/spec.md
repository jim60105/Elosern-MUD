# Spec Delta

## ADDED Requirements

### Requirement: Draft portrait lifecycle follows reset and activation ownership
Reset SHALL clear the pending wizard draft and its creation-owned portrait state together. Custom activation SHALL keep draft portrait ownership on the same subject; preset activation SHALL remove creation-owned cards/jobs before its normal portrait finalization. A rolled-back activation SHALL preserve previously committed draft portrait state.

#### Scenario: Reset cancels only creation output
- **WHEN** an owned pending character resets with a draft portrait card, pending/in-progress job or failed receipt
- **THEN** the draft and receipt are absent, the creation-owned cards and jobs are removed, its recorded draft failure is cleared, and the slot rebuilds empty; unrelated subject/card/file controls remain unchanged

#### Scenario: Reset is idempotent without a saved draft
- **WHEN** a pending character generated from unsaved form values and resets twice
- **THEN** both resets succeed, no creation-owned output remains and no automatic portrait is queued while the character stays pending

#### Scenario: Late settlement cannot resurrect canceled output
- **WHEN** a worker holding a creation job token returns after a committed reset or preset activation canceled that job
- **THEN** neither a card nor a stored output is published, temporary output is discarded, and the replacement creation/preset state is unchanged

#### Scenario: Custom activation keeps the subject and existing work
- **WHEN** a custom draft activates with a ready card or an in-flight creation portrait
- **THEN** the subject key is unchanged, existing output/work survives, and guarded activation queues no duplicate image; the pending job may settle normally after activation

#### Scenario: Untouched custom activation keeps automatic generation
- **WHEN** a custom draft activates without prior draft portrait work or a satisfying official default
- **THEN** the existing guarded post-commit automatic generation remains eligible

#### Scenario: Activation rollback preserves prior art
- **WHEN** custom or preset activation rolls back after portrait finalization/cleanup would have run
- **THEN** preexisting policy, receipt, cards, jobs and files remain, no activation-added policy/job survives, and the character remains pending with its prior draft

#### Scenario: Preset activation purges unrelated custom draft art
- **WHEN** a pending character with a creation-owned custom portrait activates a registered synthetic preset
- **THEN** its creation-owned cards/jobs are removed before preset portrait finalization, and the normal preset official/fallback/automatic guard determines the activated portrait without inheriting the custom image
