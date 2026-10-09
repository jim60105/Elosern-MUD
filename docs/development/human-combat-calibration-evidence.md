# Human Combat Calibration Runtime Evidence

This document records runtime measurements from bounded resolver probes using real Evennia objects, registered equipment, and persisted restriction overlays.

## Historical Projected Evidence vs. Runtime Measurements

Historical exploration executed 1,554 trials under projected equipment adjustments. Those outcomes established encounter bounds but did not validate persistent hosts or equipment wear restrictions. The real-runtime calibration probes below exercise the authoritative Evennia objects, `ActionResolver`, initiative, `run_round`, and `monster_behaviour_policy`.

### Summary of Sampled Real Matchups (Seeds 0–3, 200-Round Bound)

| Tier / Variant | Human Reference / Policy | Monster Defeats | Retreats | Losses | All Standing | Median Rounds | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| **F** / Grain pecker | F 224-pt creation build (plains kit: 7/5/9) | 4/4 | 0 | 0 | 4/4 | ~15 | Stand-and-fight, 0 rejects |
| **E** / Shore walker | E restricted senior (military E pair, limit ring) | 4/4 | 0 | 0 | 4/4 | ~8 | Stand-and-fight, 0 rejects |
| **D** / Wood stalker | 3× D restricted party | 4/4 | 0 | 0 | 4/4 | ~5 | Party clear, all standing |
| **C** / Cliff stepper | C restricted (real monster policy) | 1/4 | 3/4 | 0 | 4/4 | ~6 | Retreats reported separately from defeats |
| **B** / Bank lurker | Restricted B senior (military B pair) | 4/4 | 0 | 0 | 4/4 | ~2 | Clear progression |
| **High Lower** probe | Restricted B senior | 4/4 | 0 | 0 | 4/4 | ~14 | Matches lower high-tier boundary |
| **High Upper** probe | Restricted B senior | 0/4 | 0 | 4/4 | 0/4 | — | Confirms high-upper boundary challenge |
| **High Upper** probe | S senior (military S pair, domain) | 3/4 | 0 | 1/4 | 3/4 | ~54 | Upper challenge; not a comfortable guarantee |
| **Calamity Lower** probe | S senior | 0/4 | 0 | 4/4 | 0/4 | — | Calamity tier exceeds lone human |

### Simulation Discipline
- All trials resolved with `simulated=True` and action context marker `simulated: True`.
- Skill practice XP and unlock progression were strictly frozen (verified against unsimulated control).
- No ordinary defeat rewards or quest kill credits were awarded.

### Attribute Parity
- E vs. Reef warden seed 0 evaluated under Evennia SQLite database test runner matches expected deterministic victory, zero rejected actions, and round termination.
