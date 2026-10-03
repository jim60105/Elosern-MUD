## Purpose

Settles identity-addressed letters on authoritative game ticks with guaranteed NPC delivery and distinct player availability, collection, and read states.

## ADDED Requirements

### Requirement: Accepted letters have fixed guaranteed delivery

A valid bounded letter SHALL be addressed to an established recipient persistent identity. Accepted send SHALL atomically fix its body, source identity, send tick and due tick at one game hour later. Distance, movement, room instantiation, model latency and real time SHALL NOT alter delivery. NPC delivery SHALL always succeed with no failure mechanics.

#### Scenario: Recipient moves before due
- **WHEN** an accepted NPC letter reaches its due tick while the NPC is elsewhere or uninstantiated
- **THEN** it becomes delivered at the same due tick

#### Scenario: One-hour boundary
- **WHEN** an accepted letter is inspected just before and at its due tick
- **THEN** it is sent before the boundary and due exactly one game hour after send

### Requirement: Delivery follows only committed authoritative time

Settlement SHALL process due letters once using actual committed world ticks crossed by command, combat or skip, with deadline inclusion `start_tick < due_tick <= end_tick`. Player recipients SHALL become available-for-collection, not collected/read. Delivery and pending downstream work SHALL commit with clock advance and roll back with it.

#### Scenario: Interrupted or rejected skip
- **WHEN** a requested sleep/wait interval is rejected or commits less than requested
- **THEN** only actual crossed deadlines settle; rejected time settles none

#### Scenario: Late stage fails
- **WHEN** delivery settles and a later clock operation fails
- **THEN** clock, letter state and downstream progress roll back together

#### Scenario: Offline restart repeats settlement
- **WHEN** services are disabled and due settlement runs again after restart
- **THEN** NPC delivery and player availability continue with no duplicate transition

