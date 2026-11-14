Rule D3.4 evidence: none of the 52 new cells, and none of their 8 neighbours,
falls inside an `EcologyZone.rectangles` rectangle or on a
`MonsterSite.coordinates` point of `world/lore/monster_placement.py`.
Checked with the terrain-free registry read only, no habitat edited:

    checked 52 habitat conflicts [] 0

No `spacing_exemption` is used by any row of this change.

Distribution of the 52 settlements:

- 17 villages, every one on an inner trunk cell of a shared road corridor at a
  two- or three-polyline carriage; the D1 off-trunk village share is unused
  because every gap that needed a village lay on a trunk and a village off the
  trunk cannot close a road gap (tiers design §5 target, not a limit).
- 35 hamlets: 26 on an inner road cell (74%), 9 off every road (26%, target
  about 20%), each of those 1 to 3 km from the highland or border river.
- Ratio 35 hamlets to 17 villages, about one village to two hamlets.

Reading of the road facts, for the next placement change: `place.py`'s
`roads=N` count is the number of route polylines that contain a cell, not the
number of geometric forks at it. Stage-one polylines overlap along one
corridor for long stretches, so a cell can be carried by three polylines and
still be a through cell with two road contacts; every new map here has two
gates (or one, for an off-road camp), which is the real contact count. The
committed `description` and `geographic_constraint` therefore name the
terrain feature and the corridor, never a junction: an earlier draft that
called these sites junctions was corrected before the change closed.

Renames made before commit, so the ID is fixed at its final spelling:
`village_lynx_slope` became `village_lynx_den` (the display name 山貓寨 is a
den), and `hamlet_deer_slope` became `hamlet_deer_trail` because the Altoria
`hamlet_deer_slope` already exists. The plan snippets carry the final IDs.

No hamlet uses the D2 boundary exception: every one of the 52 cells reports
`"region": "northwest_highland_forest", "scope": "in"` from
`snippets/place.py context`.