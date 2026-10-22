# Spec Delta

## ADDED Requirements

### Requirement: Quest nomination observes the committed completion owner
Qualifying quest completion SHALL notify nomination only after its owning outer settlement commits a finalized completion fact. Planning SHALL NOT dispatch completion notifications. The notification SHALL carry the authoritative source identity and finalized results. Replacing an unchanged terminal record or replaying its notification SHALL NOT create another completion attempt.

#### Scenario: First acquisition completion is available at admission
- **WHEN** a real purchase supplies the final item for a player's first eligible quest completion
- **THEN** the nomination workflow begins only after purchase and completion commit and can read that new completion as material

#### Scenario: Late purchase failure discards notification
- **WHEN** a purchase fails after its quest writer recorded completion evidence but before the outer commit
- **THEN** no completion nomination begins and neither purchase effects nor completion evidence survive

#### Scenario: Completion inside an action waits for the outer owner
- **WHEN** a quest completes inside an action or automatic reward chain nested in a still-open settlement
- **THEN** no nomination is admitted until the outer owner commits; rollback discards every pending completion notification

#### Scenario: Repeated terminal replacement is inert
- **WHEN** the same completed record or committed completion notification is delivered again after the first attempt finishes
- **THEN** no second completion attempt is admitted, while independent later wake or logout remains eligible under normal rules
