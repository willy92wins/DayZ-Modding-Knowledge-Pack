# DayZ — Extracción de road graph desde .wrp (proyecto GPS / RoadGraph_Core)

> Conocimiento transversal del pipeline que convierte un mapa DayZ en el grafo de
> carreteras que consume el SDK RoadGraph_Core. Reconstruido y verificado 2026-05-14
> contra 3 mapas (Chernarus2035, Onforin x2). Spec original del formato:
> `Claude/Projects/GPS/WRP_V29_FORMAT.md`.

## Dónde vive todo

- **Pipeline (scripts):** `Claude/Projects/GPS/extractor/` — repo persistente del proyecto.
- **JSON de trabajo / archivo:** `Claude/Projects/GPS/data/`.
- **JSON que consume el SDK:** `DayZ Projects/RoadGraph_Core/data/<worldname>_roads.json`.
- **SDK Enforce:** `DayZ Projects/RoadGraph_Core/scripts/4_World/` (RGC_Manager.c carga el JSON).

⚠️ **Los scripts de los pases de conectividad se perdieron una vez** por vivir solo
en un `outputs/` temporal. Todo lo reusable DEBE estar en `extractor/` del repo.

## Pipeline completo (para un mapa nuevo)

```
cd Claude/Projects/GPS/extractor
pip install scipy --break-system-packages          # imprescindible para Pass1+2 fusion

# 1. .wrp desde el world.pbo del workshop
python extract_wrp.py extract-wrp <ruta>/world.pbo <map>.wrp

# 2. worldname real (= nombre OBLIGATORIO del JSON, NO el del workshop)
python get_worldname.py        # edita la lista de workshop IDs dentro

# 3. grafo base (Roadnet + dedup + Pass1+2 fusion)
python build_road_graph.py <map>.wrp --map <worldname> --out <worldname>_roads.json

# 4. pases de conectividad (Object section + reclass + stitch)
python apply_connectivity_passes.py <map>.wrp <worldname>_roads.json <worldname>_roads_final.json

# 5. validación visual
python validate_graph.py   <worldname>_roads_final.json --out <worldname>_validate.png
python visor_components.py <worldname>_roads_final.json <worldname>_components.png

# 6. entregar
cp <worldname>_roads_final.json  RoadGraph_Core/data/<worldname>_roads.json
# y añadir el worldname a RGC_Manager.c -> ListAvailableMaps()
```

## Formato OPRW del .wrp (v28 y v29 — layout idéntico)

- Header: `OPRW` + int32 versión (28/29) + sub-magic `0FNE` ("ENF0").
- `Models[]`: tabla de todos los `.p3d` del mapa (asciiz). Primer `.p3d` del fichero;
  el count es el int32 4 bytes antes.
- **Roadnet section**: rejilla de celdas; cada celda = int32 nLinks + N RoadLinks.
  RoadLink = ConnectionCount + Positions[] + ConnectionTypes[] + ObjectID +
  extra_v29(4B) + asciiz P3dPath + Matrix4P(48B). El extractor la localiza por
  escaneo de patrón (no por offset). Esto da el grafo base.
- **Object section** (post-Roadnet, NO documentada en spec BIS): empieza tras el
  zero-padding desde roadnet_end. Records **fixed-stride de 60 bytes**:
  `uint32 obj_id | uint32 model_idx | float matrix[12] | uint32 flags`.
  `model_idx` indexa en `Models[]`. La traslación está en matrix[9..11].
  Contiene TODO: vegetación, edificios, rocas, y **road instances** (carreteras
  puestas como objeto suelto) que el Roadnet pierde.

## Los pases de conectividad (apply_connectivity_passes.py)

1. **v2.5 road_connector** — por cada road instance de la Object section, conecta
   los 2 nodos road de COMPONENTES DISTINTAS más cercanos dentro de 30 m (60 m si
   es puente). Edge con polyline de 3 puntos [nodoA, posición_instancia, nodoB],
   surface asfalto (puente→bridge). Justificación física real: hay un `.p3d` de
   carretera ahí. Union-find vivo → idempotente.
2. **fase6 reclass** — edges con surface `other` cuyo `p3d` es una familia de
   carretera no reconocida por el clasificador base (`city_*`, `town_*`, etc.) → asfalto.
3. **fase6 stitch** — pares de nodos cross-component a < 5 m → edge `<stitch_road_5m>`.
   Cose fragmentación fina que el dedup 3D no fusionó.

`extras` del JSON registra qué añadió cada pase (`roads_v2.5_added`, `fase6_reclass`,
`fase6_stitches`, ...). Backups `.bak_*_pre_*` por pase.

Principio (HANDOFF_v4 §8.3): **nunca conectar por proximidad arbitraria** — siempre
tiene que haber un objeto físico real del .wrp justificando la conexión. El pase
v2.6 (node_pair_bridge por max_dist) se rechazó por crear conexiones falsas.

## worldname ≠ nombre del workshop  ⚠️ CRÍTICO

El SDK (`RGC_Manager.GetGraph()`) carga `data/<GetWorldName()>_roads.json`. El
worldname es la clase `CfgWorldList` del `config.bin` del `world.pbo`, NO el título
del ítem del workshop ni el nombre del `.wrp`.

- Sacarlo con `get_worldname.py` (descomprime el `config.bin`).
- Ejemplos reales: workshop "CBTONFORIN" y "Onforin STB" → ambos worldname `onforin`
  (son 2 versiones del mismo mapa, no pueden coexistir instaladas).
- El fichero JSON DEBE llamarse `<worldname>_roads.json` o el SDK no lo encuentra.

## BIS LZSS — variante de direccionamiento RELATIVO (PBO Cprs / config.bin rapified)

Los `config.bin` y entries PBO con mime `Cprs` usan LZSS, pero **NO el ring-buffer
clásico de Okumura**. Es direccionamiento **relativo al output**:

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

Errores que costaron tiempo: (a) asumir ring-buffer 4096 con prefill 0x20 — falso;
(b) asumir índice absoluto en vez de `len(out) - offset`. Implementación buena y
verificada en `extractor/get_worldname.py`.

## Estado de cobertura (2026-05-14)

9 mapas con grafo: chernarusplus, enoch, banov, deerisle, deadfall, namalsk (los 6
originales) + chernarus2035 + onforin (build CBTONFORIN; STB archivado como `.ALT_*`) + iztek (worldname asumido, config protegido).
Los mapas custom modernos vienen a 90-97% top-1 ya en crudo; los pases suben poco
porque su Roadnet está bien construido. Lo que queda suelto suelen ser islas reales.

## Ver también
- [`30_Sessions/2026-05-14-gps-3-mapas-nuevos.md`](../30_Sessions/2026-05-14-gps-3-mapas-nuevos.md) — sesión de extracción de los 3.
- `Claude/Projects/GPS/HANDOFF_2026-04-28_v4.md` — handoff del mod GPS.
- `Claude/Projects/GPS/WRP_V29_FORMAT.md` — spec byte a byte del Roadnet.
- `Claude/Projects/GPS/NOTES_2026-05-14_3_mapas_nuevos.md` — notas detalladas.

## Update 2026-05-16 — caso "dos workshop items, mismo worldname"

Una solución pragmática cuando dos workshop items comparten worldname (caso Onforin):
**esperar al autor**. Nosty homogeneizó CBTONFORIN y Onforin STB a la misma versión
(world.pbo byte-idéntico). El conflicto desaparece sin necesidad de desambiguar por
runtime. Si vuelves a encontrar dos ítems con el mismo worldname y versiones
distintas, antes de implementar disambiguation por `version`, **comprueba el MD5
de los world.pbo**: puede que el autor los haya sincronizado.

```
md5sum .../221100/<id_a>/addons/world.pbo  .../221100/<id_b>/addons/world.pbo
```

Si coinciden → un solo `<worldname>_roads.json` sirve para ambos.

## Update 2026-05-16 — caso "config protegido" (Iztek, firma zorro)

Iztek (workshop 3704583052) tiene **todos los `config.cpp` a 0 bytes** en los PBO
públicos (los `.pbo.zorro.bisign` indican un esquema de firma propietario; el
config canónico de CfgWorlds parece no estar en el PBO descargable, o está en
un formato no estándar). El descompresor LZSS no aplica — no hay `config.bin`
que descomprimir.

**Fallback al determinar el worldname cuando no hay config legible:**
1. `world.pbo` prefix (en su header PBO) — suele ser `<WorldClass>\world`.
2. Nombre interno del `.wrp` — convencionalmente coincide con la clase en minúsculas.
3. Paths internos del `.wrp` (las `.rvmat` y demás) — prefix `<worldname>\data\...`.

Para Iztek las 3 señales apuntan a `iztek`. Verificar siempre in-game con el RPT log
(`GetWorldName()` se imprime al cargar el grafo) tras el primer test.

Si `GetWorldName()` devuelve algo distinto al nombre asumido, renombrar
`<asumido>_roads.json` → `<real>_roads.json` (el SDK ya hace `.ToLower()`).

## Related

- [[dayz-wrp-road-graph-extraction]] — runbook operativo (paso a paso) de este mismo pipeline.
- [[dayz-enforce-script-reference]] — APIs Enforce del SDK RGC_Manager que consume el JSON generado.
- [[20_Knowledge/lessons-learned|lessons-learned]] — lección durable: scripts reusables van al repo `extractor/`, no a un `outputs/` temporal.
