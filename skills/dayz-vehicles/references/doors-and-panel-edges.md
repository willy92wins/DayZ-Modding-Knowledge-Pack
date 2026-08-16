# Puertas: canto abierto, tapas y desmontables que no son puertas

Extraido de `SKILL.md` (corte 3, 2026-08-15). Aqui vive el DETALLE; el enunciado
corto y cuando leer esto estan en el indice `## ARCHIVO DE LECCIONES` del SKILL.md.
Nada de este fichero esta derogado: son lecciones vigentes, ordenadas por tema en
vez de por fecha.

---

## An imported door has NO end caps, and a shut door cannot show you (SP-198, added 2026-08-07, SUB_BRZ E-1)

A ripped car door arrives as two open shells - outer skin and inner card - with
NOTHING closing the leading and trailing edges. The source game never shows that
edge, so it was never modelled. Every DayZ door OPENS, so every imported door
shows it. There are no 2D doors: assume the caps are missing until measured.

SUB_BRZ, both doors, measured at the two z extremes of the door-local frame:

| end | faces facing +/-z | cap area | expected (height x thickness) |
|---|---|---|---|
| leading | 125 | 25 cm2 | ~710 cm2 |
| trailing | 62 | 17 cm2 | ~710 cm2 |

3.5% and 2.4% of the area a real cap needs, and what remains is `brz_paint`
fold-over at the skin edge, not a band. Door thickness available at both ends:
77 mm.

**Day-0 check for any vehicle with opening doors** - slice the door at its two
extremes along its long axis, sum the area of faces whose geometric normal runs
along that axis, and compare against `height x thickness`. Under ~30% means the
caps are missing. `VehicleImport\work\s43_fixes\s49_probe_ends.py` is the probe.

**Why this hides for entire sessions, and the general lesson:** with the door
SHUT the body covers that edge, so every closed-door measurement passes. SUB_BRZ
spent five winding passes, a paint-normals fix and a black-normals fix, plus an
offline visibility oracle over 20 cameras, a jamb gap measured point-to-triangle
and a culling-correct seam raster - all on the shut door, all green, while the
defect sat in the open-door configuration nobody measured. Generalise it:
**measure a part in the state where it is EXPOSED, not in its default state.**
A green metric on the hidden configuration is not evidence about the visible one.

Corollary for the in-game checklist: a door verdict is only worth collecting with
the door OPEN, and the screenshot must show it open. Two rounds of SUB_BRZ
captures were taken shut and settled nothing.

Corollary for the fix: the caps are new geometry, not a flip. Normals and winding
passes cannot create a surface that was never there - and if a door edge reads as
"nothing at all" rather than "wrong colour" or "wrong shading", suspect absence
before orientation.

## Un canto de puerta ausente se mide por LONGITUD DE BORDE LIBRE contra el control vanilla, y tres fixes "obvios" no lo cierran (SP-202, added 2026-08-07, SUB_BRZ E-1; refina SP-198)

> ⚠ SUPERSEDIDO PARCIALMENTE por SP-245 (sección siguiente): el canto trasero SÍ falla, y el
> cierre por script SÍ funciona con fondo medido. La métrica y los 3 fixes descartados siguen
> vigentes.

SP-198 dice que una puerta importada no trae tapas de canto. Falta lo accionable: **con qué se mide
y qué no arregla**. Una sesion entera de sondas en SUB_BRZ, reproducible en cualquier coche del
pipeline con puertas desmontables.

**El control se saca en un comando** (no hace falta el coche entero):

```
python odol_to_mlod.py "DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d" ctrl.p3d
```

**La metrica correcta es longitud de borde libre por extremo del eje largo**, en una banda del 6%,
en TODOS los LODs render + el 1100. Medido:

| extremo | vanilla | SUB_BRZ | lectura |
|---|---|---|---|
| delantero (pilar A) | **0 mm** | 673 mm | defecto |
| trasero (pilar B) | 612 mm | 627 mm | **normal, no tocar** |

Dos cosas que esto corrige de golpe:

1. **Tener borde libre en el perimetro de una puerta es NORMAL.** El perimetro entero es un ciclo
   cerrado de ~4,4 m (piel exterior + cristal) y vanilla tambien lo tiene. Solo el borde DELANTERO
   es anomalo, porque es el unico que queda a la vista al abrir. Un gate que mida "borde libre
   total" da rojo en una puerta sana.
2. **El gate por area (`cap >= 70% de alto x espesor`) esta mal calibrado** y no debe usarse: asume
   espesor constante en toda la altura y que toda la altura es chapa. En una puerta frameless (BRZ,
   GT86, y cualquier coupe del rip) la mitad alta es cristal, y el "espesor" que reporta una sonda
   de banda es la CURVATURA del doblez, no un hueco. Ese gate pedia ~710 cm2 de tapa donde la
   geometria real admite ~640 y solo en parte de la altura.

**Tres fixes descartados CON MEDIDA — no repetirlos:**

- **Doble-carar la banda frontal**: render con la regla de culling calibrada del pipeline, antes y
  despues, **0 px de diferencia**. El see-through del canto no es un problema de caras de una sola
  cara.
- **Labio doblado (hem) copiando a vanilla**: un borde libre no se cierra desplazandolo; el labio
  mueve el borde, no lo elimina. Ademas la holgura contra la jamba no da: a 2 mm de profundidad ya
  hay vertices de carroceria dentro del volumen (gap puerta-jamba medido en 0,7 mm).
- **Bridge piel exterior <-> panel interior**: los dos bordes NO se corresponden. Solo 6 de 13
  franjas de altura tienen los dos bordes presentes, con huecos de 121 a 218 mm. Un bridge
  automatico produce una pared retorcida.

**La causa estructural, que es lo que hay que mirar en el coche siguiente:** la piel exterior y el
panel interior son **mallas separadas que no se tocan**. En SUB_BRZ el panel interior
(`brz_cab_plastic`, `brz_black`) muere 108 mm antes del borde delantero, donde la piel exterior
(`brz_paint`) si llega. Entre ambos no hay nada. Por eso no existen "dos anillos que puentear":
existen dos bordes de piezas distintas separados 11 cm.

**Consecuencia de planificacion:** cerrar el canto es **modelado a mano** (autorar la pared del
canto en Blender), no una cirugia por script. Presupuestalo como tal desde el principio y pide la
captura del defecto CON LA PUERTA ABIERTA antes de empezar — con la puerta cerrada toda medida da
verde (SP-198) y sin la captura no se distingue "veo a traves" de "el borde queda feo", que llevan
a fixes distintos.

Sondas reutilizables en `VehicleImport\work\s50_doorcaps\`: `s50_probe_freeedge.py` (la metrica del
gate, por LOD), `s50_compare_control.py` (control vs candidato, ejes normalizados),
`s50_probe_bridge.py` (correspondencia de los dos bordes), `s50_render_front.py` (render A/B/C:
actual con culling, sin culling, y el fix simulado).

## El canto de puerta SE CIERRA POR SCRIPT con una banda de fondo MEDIDO — y ambos cantos fallan (SP-245, added 2026-08-15, SUB_BRZ s52; supersede parcialmente SP-202)

Dos correcciones a SP-202, ambas con medida y la primera confirmada in-game por el usuario:

1. **El canto TRASERO también falla.** La adjudicación "vanilla tiene 612 mm libres ahí → normal,
   no tocar" era una inferencia mala: que vanilla tenga borde libre no implica que quede EXPUESTO.
   Con el usuario delante fallan los dos. Y medido a perímetro completo (banda z del 8%, no del
   6%): vanilla delantero **0 mm** / trasero ~502 mm; el rip 743/598 mm — el delta anómalo está en
   AMBOS extremos.
2. **"Cerrar el canto es modelado a mano" queda superseded**: una banda perimetral por script
   alcanza paridad vanilla. El fix de 5 mm de s51 fallaba por PROFUNDIDAD (5 mm en un hueco de
   ~77 mm), no por orientación — sus quads sí se dibujaban (probe cull ON == cull OFF).

**La receta que funciona** (`VehicleImport\work\s52_cantos\s52_close_perimeter.py`, ambas puertas,
LODs visuales + 1100):

- **Filo libre VERDADERO**: contar el uso de cada arista sobre TODAS las caras del LOD y quedarse
  con las de la piel con uso==1. Contar solo dentro del material de la piel (como s51) marca como
  "libres" aristas que en realidad cubre el cristal o el trim, y la banda las atraviesa.
- **Fondo medido por vértice de borde**: raycast hacia dentro por el eje del grosor; fondo = 90%
  del hueco hasta la primera pared, clamp [8, 60] mm; 60 mm donde no hay pared en 150 mm. El hueco
  real varía 10→135 mm — cualquier constante está mal en la mitad del perímetro.
- **Banda estanca**: UN punto extruido por vértice soldado del borde, compartido entre quads
  vecinos (extruir por-arista con fondos distintos deja rendijas).
- **Winding**: normal almacenada apuntando FUERA del filo, winding geométrico opuesto (la
  convención medida al 100% en los LODs render de ambas puertas). "Fuera del filo" = componente
  del (punto_medio − centroide de la piel) perpendicular a la arista, con el eje del grosor a 0.
- **Gates de paridad, siempre contra el control** en el MISMO metric: render de canto (BRZ pasó
  de 15,0% → 25,4% de superficie dibujada vs 26,8% vanilla) y barrido de rayos por el eje largo
  (65,7% de rayos limpios vs 68,8% vanilla — la puerta quedó MÁS cerrada que la control). Un
  umbral absoluto sin control falla puertas sanas: la vanilla da 68,8% de "abierto" en el barrido
  ingenuo porque la mayoría de los rayos pasan por fuera de la silueta legítimamente.
- **Diagnóstico previo que lo desbloqueó**: renderizar el canto en DOS escenas — coche MONTADO y
  CERRADO (¿regresión visible por fuera?) y puerta AISLADA (= puerta abierta, donde vive la
  queja). El defecto solo existe en la segunda; medir solo una responde a otra pregunta.

Pedir la captura del defecto CON LA PUERTA ABIERTA (SP-202) sigue vigente antes de dimensionar.

---

## Desmontables que NO son puertas: capo y maletero (medido sub_wrxsti_04, 2026-08-07)

**Nivel de evidencia: MEDIDO offline. La extension del rig NO esta implementada ni verificada
in-game a fecha de hoy.** Los numeros de abajo son geometria del modelo, no comportamiento del
motor; lo que aqui se promueve es DONDE mirar, no una receta probada.

Un rig de desmontables escrito para puertas hornea dos supuestos que son **falsos** para capo y
maletero, y ninguno de los dos canta: uno aborta con un mensaje que culpa al eje, y el otro ancla
la bisagra a un metro de donde va, en verde.

1. **El borde de bisagra no es siempre el delantero.** Una puerta bisagra en su borde delantero
   (-Z), y de ahi que los rigs banden sobre `z.min()`. Pero un **capo bisagra en su borde TRASERO**
   (el del parabrisas, +Z) y un **maletero en su borde DELANTERO** (-Z). Medido en el WRX: bisagra
   del capo a **12 mm** del maximo Z de su hoja, la del maletero a **4 mm** del minimo. El borde
   delantero del capo, que es donde bandaria un rig de puertas, esta a **1,16 m** de la bisagra
   real. El borde tiene que ser un dato declarado por rol, no una constante.

2. **La inclinacion se mide contra el eje de su CLASE, no siempre contra la vertical.** Capo y
   maletero dan **89,81 grados** y **88,84 grados** respecto de +Y: revientan cualquier presupuesto
   de verticalidad. Su eje es lateral (+X). Un gate de "tilt vs Y" no es un gate de calidad para
   ellos, es una prohibicion.

3. **Trampa de signo, y es silenciosa.** Con eje lateral `axis[1]` vale ~0, asi que la
   normalizacion habitual `if axis[1] < 0: axis = -axis` deja de ser determinista: el signo lo
   decide el ruido del PCA. La direccion de apertura tiene que venir del angulo declarado, y el
   gate offline que caza un signo invertido es **fisico**: el **borde libre** (la banda OPUESTA a
   la bisagra) debe SUBIR al abrir. Un gate de desplazamiento por magnitud (`|delta| > umbral`)
   pasa en verde con el signo invertido — mide que se mueve, no hacia donde.

4. **El gate del eje NO valida el conjunto de piezas del rol, y es facil creer que si.** El eje se
   ajusta sobre UNA pieza (la que declara la bisagra). Meter en el rol una pieza que no toca — una
   jamba, un panel de carroceria, un faro que en realidad va al paragolpes — no mueve el eje ni un
   grado: **el contraste de bisagra sigue en verde y el de apertura tambien**. Hace falta un gate
   aparte sobre la propiedad: distancia maxima de cualquier cara del rol al eje contra un radio
   declarado, mas el recuento de caras contra el censo. Sin el, la agrupacion mala llega al juego.

5. **Antes de escribir una regla de propiedad `+x`/`-x`, mide si hay caras EN el plano x=0.** Una
   regla por centroide las descarta por los dos lados y esas caras desaparecen del coche sin que
   nadie lo note. En el WRX salieron 0 de 18 piezas candidatas, pero eso es un dato medido, no una
   garantia del formato. Y para una pieza entera no hace falta regla especial si el selector cae a
   "todas" por defecto.

6. **Un capo suele traer cristal y un maletero no.** Si el codigo estructural exige cuerpo Y
   cristal para acotar sus cajas, el maletero aborta y el capo pasa — pero clasificando el cristal
   de los faros como "ventana", con su zona de dano y su material de penetracion de vidrio encima.
   La caja de cristal tiene que ser opcional, y la clasificacion cuerpo/cristal un dato, no un
   prefijo de nombre.

7. **La masa del item no se hereda de la puerta.** Un `geometry_mass_kg` global le pone a un capo
   los kilos de una puerta.

Origen: `VehicleImport\plans\2026-08-07-T6-detachables-rig-extension.md` (T6 del piloto CAMBIO-3),
sondas en el scratchpad de la sesion. Los puntos 3 y 4 los levanto una revision R22 ciega sobre el
plan, no la implementacion: son exactamente la clase de defecto que un gate offline no encuentra
porque el gate estaba midiendo otra cosa.
