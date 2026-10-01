# DayZ — Road graph extraction from .wrp (GPS / RoadGraph_Core project)

> Cross-cutting knowledge of the pipeline that converts a DayZ map into the road
> graph consumed by the RoadGraph_Core SDK. Reconstructed and verified 2026-05-14
> against 3 maps (Chernarus2035, Onforin x2). Original format spec:
> `Claude/Projects/GPS/WRP_V29_FORMAT.md`.

## Where everything lives

- **Pipeline (scripts):** `Claude/Projects/GPS/extractor/` — persistent project repo.
- **Working JSON / archive:** `Claude/Projects/GPS/data/`.
- **JSON consumed by the SDK:** `DayZ Projects/RoadGraph_Core/data/<worldname>_roads.json`.
- **Enforce SDK:** `DayZ Projects/RoadGraph_Core/scripts/4_World/` (RGC_Manager.c loads the JSON).

⚠️ **Connectivity pass scripts were lost once** because they lived only
in a temporary `outputs/`. Everything reusable MUST be in the repo's `extractor/`.

## Complete pipeline (for a new map)

```
cd Claude/Projects/GPS/extractor
pip install scipy --break-system-packages          # imprescindible para Pass1+2 fusion

# 1. .wrp from workshop world.pbo
python extract_wrp.py extract-wrp <ruta>/world.pbo <map>.wrp

# 2. real worldname (= MANDATORY JSON name, NOT the workshop one)
python get_worldname.py        # edit the workshop ID list inside

# 3. grafo base (Roadnet + dedup + Pass1+2 fusion)
python build_road_graph.py <map>.wrp --map <worldname> --out <worldname>_roads.json

# 4. pases de conectividad (Object section + reclass + stitch)
python apply_connectivity_passes.py <map>.wrp <worldname>_roads.json <worldname>_roads_final.json

# 5. visual validation
python validate_graph.py   <worldname>_roads_final.json --out <worldname>_validate.png
python visor_components.py <worldname>_roads_final.json <worldname>_components.png

# 6. entregar
cp <worldname>_roads_final.json  RoadGraph_Core/data/<worldname>_roads.json
# and add the worldname to RGC_Manager.c -> ListAvailableMaps()
```

## OPRW format of .wrp (v28 and v29 — identical layout)

- Header: `OPRW` + int32 version (28/29) + sub-magic `0FNE` ("ENF0").
- `Models[]`: table of all `.p3d` files of the map (asciiz). First `.p3d` of the file;
  the count is the int32 4 bytes before.
- **Roadnet section**: cell grid; each cell = int32 nLinks + N RoadLinks.
  RoadLink = ConnectionCount + Positions[] + ConnectionTypes[] + ObjectID +
  extra_v29(4B) + asciiz P3dPath + Matrix4P(48B). The extractor locates it by
  pattern scan (not by offset). This gives the base graph.
- **Object section** (post-Roadnet, NOT documented in BIS spec): starts after the
  zero-padding from roadnet_end. Records **fixed-stride of 60 bytes**:
  `uint32 obj_id | uint32 model_idx | float matrix[12] | uint32 flags`.
  `model_idx` indexes into `Models[]`. Translation is in matrix[9..11].
  Contains EVERYTHING: vegetation, buildings, rocks, and **road instances** (roads
  placed as loose objects) that Roadnet misses.

## The connectivity passes (apply_connectivity_passes.py)

1. **v2.5 road_connector** — for each road instance in the Object section, connects
   the 2 closest road nodes from DIFFERENT COMPONENTS within 30 m (60 m if
   it is a bridge). Edge with 3-point polyline [nodeA, instance_position, nodeB],
   surface asphalt (bridge→bridge). Real physical justification: there is a road
   `.p3d` there. Live union-find → idempotent.
2. **fase6 reclass** — edges with surface `other` whose `p3d` is a road family
   not recognized by the base classifier (`city_*`, `town_*`, etc.) → asphalt.
3. **fase6 stitch** — cross-component node pairs at < 5 m → edge `<stitch_road_5m>`.
   Stitches fine fragmentation that 3D dedup did not merge.

JSON `extras` records what each pass added (`roads_v2.5_added`, `fase6_reclass`,
`fase6_stitches`, ...). Backups `.bak_*_pre_*` per pass.

Principle (HANDOFF_v4 §8.3): **never connect by arbitrary proximity** — there must
always be a real physical object from the .wrp justifying the connection. The
v2.6 pass (node_pair_bridge by max_dist) was rejected for creating false connections.

## worldname ≠ workshop name  ⚠️ CRITICAL

The SDK (`RGC_Manager.GetGraph()`) loads `data/<GetWorldName()>_roads.json`. The
worldname is the `CfgWorldList` class of the `world.pbo` `config.bin`, NOT the title
of the workshop item nor the name of the `.wrp`.

- Extract it with `get_worldname.py` (decompresses the `config.bin`).
- Real examples: workshop "CBTONFORIN" and "Onforin STB" → both worldname `onforin`
  (they are 2 versions of the same map, cannot coexist installed).
- The JSON file MUST be named `<worldname>_roads.json` or the SDK will not find it.

## BIS LZSS — RELATIVE addressing variant (PBO Cprs / config.bin rapified)

The `config.bin` and PBO entries with mime `Cprs` use LZSS, but **NOT the classic Okumura
ring-buffer**. It is addressing **relative to the output**:

```python
def bis_lzss(data, expected):
    out = bytearray(); src = 0; flags = 0
    while len(out) < expected and src < len(data):
        flags >>= 1
        if (flags & 0x100) == 0:
            flags = data[src] | 0xFF00; src += 1
        if flags & 1:                          # bit=1 -> literal
            out.append(data[src]); src += 1
        else:                                  # bit=0 -> back-reference relativa
            b1, b2 = data[src], data[src+1]; src += 2
            offset = b1 | ((b2 & 0xF0) << 4)    # 12 bits
            count  = (b2 & 0x0F) + 3           # 3..18
            if offset == 0: break
            start = len(out) - offset          # RELATIVO a la longitud actual
            for k in range(count):
                out.append(out[start + k])     # copia con solape permitido
    return bytes(out)
```

Errors that cost time: (a) assuming 4096 ring-buffer with 0x20 prefill — false;
(b) assuming absolute index instead of `len(out) - offset`. Good implementation and
verified in `extractor/get_worldname.py`.

## Coverage status (2026-05-14)

9 maps with graph: chernarusplus, enoch, banov, deerisle, deadfall, namalsk (the 6
original ones) + chernarus2035 + onforin (CBTONFORIN build; STB archived as `.ALT_*`) + iztek (assumed worldname, protected config).
Modern custom maps come at 90-97% top-1 already raw; passes increase little
because their Roadnet is well constructed. What remains loose are usually real islands.

## See also
- [`30_Sessions/2026-05-14-gps-3-mapas-nuevos.md`](../30_Sessions/2026-05-14-gps-3-mapas-nuevos.md) — extraction session of the 3.
- `Claude/Projects/GPS/HANDOFF_2026-04-28_v4.md` — GPS mod handoff.
- `Claude/Projects/GPS/WRP_V29_FORMAT.md` — byte-by-byte spec of the Roadnet.
- `Claude/Projects/GPS/NOTES_2026-05-14_3_mapas_nuevos.md` — detailed notes.

## Update 2026-05-16 — case "two workshop items, same worldname"

A pragmatic solution when two workshop items share a worldname (Onforin case):
**wait for the author**. Nosty homogenized CBTONFORIN and Onforin STB to the same version
(byte-identical world.pbo). The conflict disappears without needing to disambiguate at
runtime. If you find two items with the same worldname and different versions
again, before implementing disambiguation by `version`, **check the MD5
of the world.pbo files**: the author may have synchronized them.

```
md5sum .../221100/<id_a>/addons/world.pbo  .../221100/<id_b>/addons/world.pbo
```

If they match → a single `<worldname>_roads.json` works for both.

## Update 2026-05-16 — caso "config protegido" (Iztek, firma zorro)

Iztek (workshop 3704583052) has **all `config.cpp` at 0 bytes** in the public
PBOs (the `.pbo.zorro.bisign` indicate a proprietary signature scheme; the
canonical CfgWorlds config seems not to be in the downloadable PBO, or is in
a non-standard format). The LZSS decompressor does not apply — there is no `config.bin`
to decompress.

**Fallback when determining the worldname when there is no readable config:**
1. `world.pbo` prefix (in its PBO header) — usually `<WorldClass>\world`.
2. Internal name of the `.wrp` — conventionally matches the class in lowercase.
3. Internal paths of the `.wrp` (the `.rvmat` and others) — prefix `<worldname>\data\...`.

For Iztek the 3 signals point to `iztek`. Always verify in-game with the RPT log
(`GetWorldName()` is printed when loading the graph) after the first test.

If `GetWorldName()` returns something other than the assumed name, rename
`<assumed>_roads.json` → `<real>_roads.json` (the SDK already does `.ToLower()`).

## Related

- [[dayz-wrp-road-graph-extraction]] — operational runbook (step by step) of this same pipeline.
- [[dayz-enforce-script-reference]] — Enforce APIs of the RGC_Manager SDK that consumes the generated JSON.
- [[20_Knowledge/lessons-learned|lessons-learned]] — durable lesson: reusable scripts go to the `extractor/` repo, not to a temporary `outputs/`.
