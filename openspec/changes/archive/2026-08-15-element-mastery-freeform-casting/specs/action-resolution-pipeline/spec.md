## ADDED Requirements

### Requirement: ActionRequest carries an optional scale modifier and a new rejection category
The frozen `ActionRequest` dataclass SHALL gain a `scale: float = 1.0` field. `1.0` SHALL remain the
behavior-preserving default for every existing construction site (the field is never required, and a
request with `scale == 1.0` behaves exactly as before this change). `RejectReason` SHALL gain the
member `SCALED_CAST_FORBIDDEN` for the freeform-casting gate. Every registered effect handler SHALL
accept a `scale: float` argument (last position) invoked by the single call site in step 5; handlers
that do not scale magnitudes SHALL ignore it. The resource-cost read SHALL become
`_adjusted_costs(actor, skill, scale=1.0)`, and step 2 and step 6 SHALL both pass the request's
scale to it, so preflight and deduction always compare and deduct the same scaled amount. No step
count, ordering, or atomicity property of the pipeline SHALL change.

#### Scenario: Existing requests default to scale one
- **WHEN** an `ActionRequest` is constructed without a `scale` argument, and a pre-existing request
  construction is replayed
- **THEN** its `scale` equals `1.0` and resolution behaves identically to the pre-change behavior

#### Scenario: Scale reaches the resource steps and the handlers
- **WHEN** a request carries `scale == 2.0` and resolves successfully
- **THEN** step 2 and step 6 both read `_adjusted_costs(actor, skill, scale)` and compare and deduct
  the scaled MP cost, the registered effect handlers receive the request's scale, and the pipeline
  still commits exactly one atomic operation

#### Scenario: The rejection category is available
- **WHEN** the freeform gate rejects a request
- **THEN** the `ActionResult` carries `reason == RejectReason.SCALED_CAST_FORBIDDEN` and the ordinary
  rejected result shape (no event log, no time cost)
