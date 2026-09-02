## ADDED Requirements

### Requirement: Worker claim and settle emit boundary events

The art worker SHALL emit one `sd_job_claim` info event when it claims a
queue record and one `sd_job_settled` info event when the record settles,
with `job`, `subject`, and — on settle — `status` and the settle `reason`
code, through the `world.observability` facade. Claim/settle ordering,
idempotency, and the single-concurrency-slot invariant MUST NOT change.

#### Scenario: A generated asset leaves a claim/settle pair

- **WHEN** the worker claims one queued subject and generation settles
- **THEN** one `sd_job_claim` and one `sd_job_settled` event are logged with
  the job identity, subject, final status, and reason code

#### Scenario: A claim failure releases the slot visibly

- **WHEN** claiming raises and the worker releases its slot and re-raises
- **THEN** a facade event carries the exception before propagation, and no
  `sd_job_settled` event is emitted for the unclaimed record
