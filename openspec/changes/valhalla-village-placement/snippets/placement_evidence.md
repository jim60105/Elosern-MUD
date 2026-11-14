Rule D3.4 evidence: none of the 52 new cells, and none of their 8 neighbours,
falls inside an `EcologyZone.rectangles` rectangle or on a
`MonsterSite.coordinates` point of `world/lore/monster_placement.py`.
Checked with the terrain-free registry read only, no habitat edited:

    checked 52 habitat conflicts [] 0

No `spacing_exemption` is used by any row of this change.

Distribution of the 52 settlements:

- 17 villages, every one on an inner trunk cell of a two- or three-road
  junction; the D1 off-trunk village share is unused because every gap that
  needed a village lay on a trunk and a village off the trunk cannot close a
  road gap (tiers design §5 target, not a limit).
- 35 hamlets: 26 on an inner road cell (74%), 9 off every road (26%, target
  about 20%), each of those 1 to 3 km from the highland or border river.
- Ratio 35 hamlets to 17 villages, about one village to two hamlets.

No hamlet uses the D2 boundary exception: every one of the 52 cells reports
`"region": "northwest_highland_forest", "scope": "in"` from
`snippets/place.py context`.