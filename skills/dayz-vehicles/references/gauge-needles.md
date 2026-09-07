# Agujas y esferas del salpicadero

Medido en el LFQuad3 del 2026-09-03 al 2026-09-07. Diecisiete trampas numeradas, tres
trampas silenciosas de la derivacion (en ingles), un instrumento, una receta y
el panel de gasolina desde cero. El cuadro del LFQuad3 dado por bueno en juego
el 2026-09-06: "el dashboard esta bien ya" (veredicto del usuario en chat,
recogido en `LFQuad3_dev\HANDOFF.md`; build `5ac339d3`). Veredicto global; no
desgloso por reloj. Sigue sin desglosar: que la aguja de gasolina se mueva con
el deposito; que la esfera pintada no gire con las agujas (el disco original
del objeto viaja en la seleccion animada; [SUPUESTO] queda ocluido); que el
reposo caiga exactamente en el cero impreso (medido offline con el gate, no
desglosado en juego). LFQuad2 confirmado en juego el 2026-09-07 00:15 (agente,
build `77303210b92d63bd`); tabla "Estado de confirmacion".

## La pieza: `_shared_parts/gauge_needles/`

`DayZ Projects\_shared_parts\gauge_needles\` — `needle_large` y `needle_small`,
cada una en `.p3d` (para soltar) y `.obj` (para editar), mas su README.

| | largo | ancho | grosor | tris |
|---|---|---|---|---|
| `needle_large` | 0,02596 m | 0,00714 m | 0,00261 m | 182 |
| `needle_small` | 0,01298 m | 0,00357 m | 0,00130 m | 182 |

La pequena es la grande al 50 %. Medidas SIN escalar: si el vehiculo de destino
aplica un escalado uniforme, multiplicar.

**Caras de reloj oficiales** en `dial_faces/`: `dial_kmh_official.png`
(0-150 km/h), `dial_rpm_official.png` (0-6 x1000, con el rojo de 5 a 6) y
`dial_fuel_official.png` (panel E / medio / F). Arte propio del proyecto, no
importado; sustituyen a las esferas del ATV original, que venian impresas 0-120
y 0-8, y esta ultima **en antihorario** — de ahi que una aguja que gira
antihorario sobre ella pueda estar bien. **Comprobar el sentido en que esta
IMPRESA la cara antes de tocar ningun angulo.**

Las dos van en **pose canonica** — pivote en el origen, punta a **+X**, eje de
giro a **+Z** — con `needle_pivot`, `needle_axis` y `needle_tip` en la Memory
LOD. Montarlas es una traslacion al centro de la esfera mas una rotacion que
lleve +Z a su normal. **La pose ES la parte reutilizable**: una aguja guardada
con el angulo y el sitio que le puso su OBJ no le sirve a otro modelo.

El pivote es el centroide del submesh **Black**, no el del conjunto: ese es el
buje sobre el que gira.

**Estado de la biblioteca (regenerada 2026-09-07).** `build_needle_library.py`
extrae la aguja con la regla de `canonical_needle` (corte por RADIO, trampa
14): 182 tris LOD0 = aro del buje 32 quads (64) + tapa 32-gono (30) +
faldon del buje 32 quads (64) + pala de 2 octagonos (12) y 6 laterales
(12); selecciones por radio `hub` (158) y `blade` (24); trasera de la pala
en z = 0 y toda la pieza con z >= 0 (la tapa del buje queda un pelo por
delante de la raiz de la pala). Conjunto de vertices IDENTICO al que
devuelve `canonical_needle` sobre el OBJ (medido, 0 faltan, 0 sobran). La
version del 2026-09-03 salia por ANCHURA ANGULAR (`THIN_DEG = 5.0`) y
tenia 86 tris: los dos octagonos ENTEROS de la pala (punta real, a
0.880 r_obj) mas 5 de sus 6 laterales, sin la tapa ni el faldon del buje, y
con la pala DETRAS del plano del buje (z -0.00261..0): incompleta y mal
puesta, no una astilla en la punta. Mala no es lo mismo que invisible:
montada tal cual en el LFQuad2, la pala queda +1.89 mm DELANTE del disco
pintado y se ve (sonda de profundidad de esa sesion, 2026-09-06); la
visibilidad la decide el `lift` del disco de cada cuadro, no la pieza.
LFQuad2 adopta la version nueva en una tanda propia con su gate; hasta
entonces monta la vieja.

## Trampa 1 — el objeto que se llama «aguja» no es una aguja

`aguja_derecha` del OBJ del LFQuad3 son **105 caras**. Topologia medida en el
marco del ensamblador (`needle_parts_probe.py`; dibujo `needle_parts.png`):

| pieza | caras | r canonico | z respecto al buje |
|---|---|---|---|
| buje: anillo `Black` + tapa 32-gono | 32 + 1 | <= 0.0029 | 0 |
| faldon del buje: 32 quads `Gauges` (collar cerrado de 360 grados) | 32 | 0.0029 .. 0.0036 | -0.0026 .. 0 |
| pala: 2 octogonos + 6 quads laterales `Gauges` | 8 | 0.0029 .. 0.02239 | -0.0026 .. -0.0009 |
| disco: 32 quads `Gauges` | 32 | 0.0036 .. 0.02544 | -0.00235 (plano) |

El buje son 33 caras mas 32 de faldon, la pala 8, el disco 32 (el faldon iba
contado como pala hasta que se midio su extension angular, 2026-09-07).
Guardarlo entero mete un reloj en la biblioteca con nombre de aguja.

Y los numeros no lo delatan: la caja del objeto sale `0,0509 x 0,0509 x 0,0026`,
que parece razonable hasta que uno se fija en que 0,0509 es exactamente el
DIAMETRO del disco. **Lo destapo dibujar la silueta**, no medirla. La punta de
la pala esta al 0.88 del r_max del objeto; el vertice mas lejano es del DISCO.

Separacion: **corte por radio**, no por anchura angular. `r_obj` = radio maximo
en el plano de todo el objeto; se DESCARTAN las caras no-Black con algun
vertice a r > 0.95 * r_obj, y se EXIGE que sean exactamente 32 caras OBJ /
64 tris (`SystemExit` si no: `canonical_needle` en `assemble_lfquad3.py`). La
z canonica se desplaza para que la trasera de la pala quede en 0. El filtro
por anchura angular (umbral 5 grados, "aro 32 + pala 7") es la forma 1: un
triangulo de la pala pegado al pivote abarca mucho angulo POR ESTAR CERCA, no
por ser un gajo, y deja 10 tris de astilla en la punta. Invisible en juego en
el LFQuad3. La biblioteca del 2026-09-03 salia de esa misma regla con OTRO
resto (los dos octagonos enteros y 5 laterales, sin tapa, pala detras del
buje; censo, arriba): la regla da piezas distintas segun donde se aplique, y
ninguna es la aguja.

## Trampa 2 — el marco de la esfera sale ARBITRARIO, y un giro no arregla un espejo

Para mapear una textura polar sobre la cara del reloj hace falta una pareja de
ejes en el plano. Si se saca con un `basis_from_axis(normal)` generico, la
pareja es **cualquiera** perpendicular al eje: el reloj sale con un roll
arbitrario. Lo que suele pasar entonces es que alguien corrige a ojo con un
`+ math.pi`, y ahi empieza el problema.

Sintoma real: el texto se leia boca abajo, se anadio media vuelta, y paso a
verse **espejado**. Media vuelta es una rotacion y no puede deshacer una
reflexion. El mapeo era `u <- -b`, `v <- -a`: un intercambio de ejes MAS una
negacion, que es una reflexion. **Ningun offset angular la quita.**

El producto vectorial solo tampoco basta. El generador del LFQuad3 construia
`u = cross(w, axis)` y afirmaba que eso es la derecha de pantalla "cuando el
eje apunta al observador". En este modelo ese `u` sale +X y la derecha del
conductor es -X: lo dice el propio modelo, que escribe `light_left` en x +0.373
y `light_right` en x -0.374 (`memory_lod`, `assemble_lfquad3.py`). Eso es la
raiz del espejo que sobrevivio tres ciclos (LL-464): el render de verificacion
montaba su marco con la MISMA expresion, reproducia el fallo y lo llamaba
correcto.

**El arreglo es anclar, no compensar:**

```python
MODEL_RIGHT = (-1.0, 0.0, 0.0)   # from light_right - light_left
w = normalizar(arriba - eje * dot(arriba, eje))   # vehicle-up, in plane
u = normalizar(cross(w, eje))
if dot(u, MODEL_RIGHT) < 0:
    u = -u
# fatal if the markers disagree with MODEL_RIGHT (memory_lod writes both)
u_uv = uc + k * dot(radial, u)
v_uv = vc - k * dot(radial, w)     # sign is MEASURED; see trap 10
```

`dial_basis` orienta `u` contra `MODEL_RIGHT`. `memory_lod` lanza `SystemExit`
si el signo de `light_right - light_left` en x deja de concordar. El mapeo
final es `(uc + k*<radial,u>, vc - k*<radial,w>)`: +U a la derecha del
conductor, -V hacia arriba porque V=0 es el borde SUPERIOR de la imagen
(`polar_uv`).

> **El signo de la V de este fragmento NO es universal.** Aqui va con menos
> porque en esta cadena V=0 es el borde superior de la imagen. Con `+` el arte
> del LFQuad3 salio **espejado en vertical** dos ciclos seguidos. La trampa 10
> da el procedimiento para acreditar el signo en TU cadena y para distinguir
> un espejo de un giro.

Sin `atan2`: el angulo solo servia para recomponer lo que ya son las dos
coordenadas del punto, y al recomponerlo intercambiaba los ejes.

**El sentido de la V se MIDE en tu propia cadena; no se hereda de aqui.** Lo
que se midio en el LFQuad3: escribiendo la V complementada, el render del
atlas reproducia EXACTAMENTE el espejado que reportaba el usuario; con la V
naive el render salia bien y el juego mal.

> **Acotacion 2026-09-04.** Este parrafo decia antes "porque el motor la
> invierte al muestrear", como si fuera un hecho del motor. No lo es: **el
> complemento vive en el ensamblador**. `assemble_lfquad3.py:1971` hace
> `uv.append((u, 1.0 - v))` sobre TODA UV que toma del OBJ, de modo que la V
> que acaba en el `.p3d` es `1 - v_obj`, y las esferas solo tienen que ser
> coherentes con ella.
>
> Contramedida de otra sesion sobre el LFQuad2, cuyas UV son del artista de
> Bohemia en un MLOD de Arma 2 y nunca pasan por ese `1-v`: con la V tal cual
> el arte sale derecho y legible, y con `1-v` el modelo muestrea **otra region
> del atlas**, no un espejo. No se contradicen: son cadenas distintas, y el
> motor solo tiene un convenio.
>
> **La regla operativa no es un signo, es un procedimiento:** la V de las
> esferas se escribe en el MISMO sentido que ya usan las demas UV del modelo,
> y ese sentido se averigua con un **control positivo** -- una pieza de arte
> cuya orientacion no admita discusion (un texto, una pegatina legible),
> renderizada con las UV reales del `.p3d`. Equivocarse produce o un espejo o
> una traslacion, los dos "plausibles": sin ese ancla no se distinguen.
>
> El cuadro del LFQuad3 se dio por bueno en juego el 2026-09-06 ("el dashboard
> esta bien ya", build `5ac339d3`): marco anclado, caras recien convertidas y
> aguja de gasolina nueva. No se desgloso por reloj. Sigue sin desglosar el
> movimiento de `fuel`, el disco original dentro de la seleccion animada, y el
> cero exacto (gate offline). LFQuad2: su marco por producto vectorial SI se
> comprobo contra los faros el 2026-09-06 (`light_left` x +0.3011,
> `light_right` x -0.3131, derecha = -X; `<u, light_right - light_left>` =
> -0.6142; det +164.81 en los dos discos): ESPEJADO, la misma raiz que aqui, y
> LL-464 pasa de una observacion a dos, en modelos y cadenas distintos. Negar
> `angle0`/`angle1` el 4-sep fue una compensacion coherente consigo misma:
> agujas clavadas en el numero correcto sobre una cara escrita al reves. Esa
> sesion lo corrigio y desplego (UV de los 64 gajos reescritas en los tres LOD
> con la derecha leida del modelo y guard fatal; det -164.81; `LFQuad2.pbo`
> sha `77303210b92d63bd`). Confirmado en juego el 2026-09-07 00:15 (agente,
> ciclo con `@CF` + `@VPPAdminTools` + `@SurvivorAnims`): velocimetro 0-150
> HORARIO, "km/h" legible, rojo a la DERECHA, aguja en el 0; cuentavueltas
> 0-6 HORARIO, "RPM x1000" legible, rojo a la derecha, aguja en el 0. El
> veredicto del usuario sobre ese build nombra otros tres defectos (gasolina
> ausente, discos fuera de la seleccion animada, textura pixelada; trampas 9
> y 15), ninguno del marco. Lo que discrimina el espejo es la medida contra
> los faros.

**Instrumento que cierra esto**: rasterizar las caras del reloj del `.p3d` YA
CONSTRUIDO con sus UV reales, muestreando la textura con la V del motor. Eso
es lo que se vera en el juego. Un render sintetico sobre un disco inventado no
vale — no lleva las UV que el modelo escribio. En el LFQuad3 ese cierre es
`dial_gate_final.py`, que toma la derecha de `LIGHT_RIGHT_MINUS_LEFT`.
`dial_render_v5.py` (y su `view_all_fix.png` del 4-sep) montaba el marco con
`cross(-axis, up)`, la misma expresion que el generador: reproducia el fallo y
lo llamaba correcto (LL-464). No vale como cierre.

**Regla de quiralidad para una pieza NUEVA** (medido 2026-09-07, LFQuad2).
LFQuad2 reintrodujo el espejo de LL-464 en su propio codigo al montar el
marco del panel: hacia `Up = cross(Np, Rp)` y, si Up salia invertido,
volteaba Up Y recalculaba Rp, lo que arrastro Rp a la izquierda del
conductor (`<Rp, der> = -1.0000`); lo cazo un guard, no un ojo. El marco
de una pieza nueva se PROYECTA del marco anclado (Gram-Schmidt sobre la
normal de la pieza), nunca se reconstruye con un producto vectorial ni se
voltea por componentes. Se comprueba la QUIRALIDAD contra el marco de
los relojes (`<u_pieza, derecha anclada>` > 0), porque de ella depende
el signo de angle0 = reposo - theta. El marco anclado de arriba si sale
de un `cross`, porque su unico grado de libertad se fija contra
`MODEL_RIGHT` medido; la pieza nueva no tiene ancla propia y lo hereda.

## Trampa 3 — cambiar el marco INVALIDA `angle0`, y ademas invierte el giro

`angle0` gira la aguja **desde el angulo con el que esta modelada**, no hasta
uno absoluto: `angle0 = cero_pintado - angulo_de_la_malla`, ambos en el mismo
marco.

Desespejar la esfera **mueve el cero pintado a otro sitio fisico**, asi que los
`angle0` viejos dejan de valer aunque nadie haya tocado la aguja. Y como la
relacion entre el marco viejo y el nuevo es una **reflexion**
(`theta_nuevo = C - theta_viejo`), tambien se invierte el sentido de giro: lo
que el motor movia en antihorario pasa a leerse horario.

Como se rederiva sin adivinar (instrumento, mas abajo):

1. Medir el **arco pintado** en el atlas (los extremos del anillo de ticks).
2. Medir el **angulo de la malla** de la aguja en el marco nuevo, del `.p3d`
   construido: del pivote al vertice mas lejano de la pala (no del objeto).
3. `angle0 = reposo - theta(minValue)` y `angle1 = reposo - theta(maxValue)`
   en el marco anclado. El gate dibuja la aguja sobre CADA valor impreso.

Los numeros del 2026-09-03 (`C = 443` del velocimetro, 225 viejo -> 218
medido, prediccion 290.3 contra 298) se dedujeron en el marco espejado: estan
**superados**. Los valores que lleva el mod dado por bueno estan en la
seccion del instrumento y en `generated/model.cfg`.

**Ojo con medir el arco por los extremos del anillo**: puede haber ticks de
entrada y salida mas alla de la ultima etiqueta. En el cuentavueltas del LFQuad3
los ticks abarcan 299 grados y la escala impresa 240.

**Si el tope del vehiculo pasa del ultimo numero impreso**, no se estira
`maxValue` dejando los angulos: eso hace que la aguja mienta en todo el
recorrido. Se alarga el barrido en proporcion y se aprovecha el hueco sin
pintar. Ejemplo con el arte viejo del ATV (impreso 0-120): 270 grados son 2,25
por km/h; con tope 150 el barrido seria 337,5 y los 67,5 de mas cabrian en los
90 grados de hueco. Con la cara oficial (impresa 0-150, recta ajustada a 0-100 y
extrapolada) el barrido es 302,8: seccion del instrumento. **Los numeros
impresos siguen siendo verdad a cualquier velocidad.**

## Trampa 4 — la posicion de reserva del eje apunta al reloj equivocado en silencio

Si el codigo escribe una posicion cableada para `<sel>_axis` y luego
`apply_needle_axis` la recalcula, esa reserva no se prueba nunca. Al intercambiar
que aguja mueve que reloj, la reserva se quedo apuntando al otro — y no da error:
si algun dia el calculo no encuentra la aguja, la aguja gira sobre la esfera
equivocada. **Una constante que solo se usa cuando algo falla hay que cambiarla
con lo demas.**

Caso medido (intercambio kmh/rpm del 2026-09-04): toco dos sitios y dejo un
tercero (etiquetas de seleccion de la aguja en `build_visual`). Resultado:
`kmh_axis` en x +0.046 y la seleccion `kmh` en x -0.045 — la aguja girando
sobre un pivote del otro lado del salpicadero. Eje, malla de la aguja y
textura cambian JUNTOS, y la reserva cableada del eje tambien.

## El contrato de cableado

1. La geometria en una seleccion con nombre propio (p. ej. `kmh`).
2. En la Memory LOD, dos puntos: el pivote (centroide del cubo Black de la
   aguja) y el pivote mas la normal HACIA el conductor, alineada contra una
   referencia fija (`n_pilot` en el LFQuad3), con el nombre `<seleccion>_axis`.
3. El hueso en el skeleton (`skeletonBones[]`), colgando del salpicadero
   (`kmh`/`rpm`/`fuel` de `drivewheel` en el LFQuad3). `sections[]` solo si la
   seleccion cambia de textura o material; las agujas del LFQuad3 no estan en el.
4. Esfera pintada 1.2 mm detras de la aguja (`lift = 0.0012` a lo largo de
   `ring_n`, que apunta lejos del conductor) y delante del panel. Aguja entera
   por delante del panel (z >= 0 en pose canonica; pivote de fuel 0.0004 m
   adelantado). Un `lift` de -0.0003 dejo las agujas invisibles desde todas
   las vistas.
   - **Dos signos por cara nueva, copiados de las vecinas** (trampa 17): winding con
     el mismo `sign(<cross, eje>)` que los discos visibles, y normal almacenada con
     `<normal, cross> >= 0` en cada vertice. Gate: `normal_sign.py`, 0 caras marcadas
     y la misma columna de signo en todas las selecciones del cuadro.
5. Una textura por reloj, potencia de dos (relleno, no estirado). rvmat PROPIO
   con normal y especular planos (`#(argb,8,8,3)color(0.5,0.5,1,1,NOHQ)` y
   `color(1,0,1,1,SMDI)`, atestados en vanilla; hallazgo de LFQuad2). Discos y
   agujas FUERA de las `hiddenSelections` de color (`camo1`): si no, la
   variante les pisa la textura.
6. En `CfgModels`, las tres clases. Valores del LFQuad3 (medido 2026-09-06):

```
class IndicatorSpeed
{
    type = "rotation";
    source = "speed";        // km/h
    selection = "kmh";
    axis = "kmh_axis";
    memory = 1;
    minValue = 0;
    maxValue = 150;
    angle0 = "rad 232.5";
    angle1 = "rad 535.3";
};
class IndicatorRPM
{
    type = "rotation";
    source = "rpm";
    selection = "rpm";
    axis = "rpm_axis";
    memory = 1;
    minValue = 0;
    maxValue = 1;
    angle0 = "rad 213.1";
    angle1 = "rad 456.4";
};
class IndicatorFuel
{
    type = "rotation";
    source = "fuel";
    selection = "fuel";
    axis = "fuel_axis";
    memory = 1;
    minValue = 0;
    maxValue = 1;
    angle0 = "rad -129.1";
    angle1 = "rad -47.6";
};
```

**Todo `angle*` lleva su unidad.** Un numero pelado lo lee el motor en
**radianes** mientras el resto del fichero va en grados: `30` acaba siendo 1718
grados.

**Unidades de las fuentes**: `speed` es **km/h** — `scripts/3_game/vehicles/car.c:113`
declara `proto native float GetSpeedometer()` y
`4_World/classes/useractionscomponent/actions/interact/actiongetouttransport.c:33`
documenta la unidad al comparar contra `GetSpeedometerAbsolute()`. `rpm` viene
normalizada 0..1 sobre `rpmMax` (en el LFQuad3 el ultimo punto de `torqueCurve`
es 6400; la esfera imprime hasta 6000, asi que `maxValue 1.0` son 6.4 unidades
impresas y `angle1` sale de theta(6.4)).

`speed`, `rpm`, `fuel` y `coolant` **son fuentes nativas del motor**, medido en el
ODOL de dos coches vanilla de 1.29 -- `offroadhatchback` (35 clases de animacion) y
`civiliansedan` (51) -- leidos con `dayz-p3d-debinarizer/scripts/odol_reader.py`. Los
dos llevan `IndicatorFuel { source = "fuel"; }` sobre el hueso `dial_fuel`, y ninguna
de sus animaciones de cuadro pasa por `AnimationSources` de script.

> **Correccion 2026-09-04.** Este parrafo decia antes que de `fuel` "no consta" que
> sea fuente del motor, porque en los scripts solo aparece `GetFluidFraction()`. Era
> falso, y contradecia una tabla que ya estaba medida en el mismo proyecto.
> **Ausencia en el lado de script no es ausencia en el motor**: las fuentes de
> `model.cfg` son nativas y no tienen por que asomar en Enforce. El aviso ya costo una
> retractacion en otra sesion, que lo repitio al usuario antes de comprobarlo.

El LFQuad3 lleva `source = "fuel"` y el usuario dio el cuadro por bueno, pero el
movimiento de esa aguja **no esta desglosado** en juego.

`dashboardMatOn`/`dashboardMatOff` es el material de la luz del cuadro; no tiene
que ver con las agujas.

Al montar una aguja desde un objeto que trae disco, el disco **NO entra** en la
seleccion animada. En el LFQuad3 el disco original de cada aguja viaja dentro
de `kmh`/`rpm` ([SUPUESTO] queda ocluido por la esfera nueva; el usuario no lo
desgloso).

## Nombres

La unidad la decide la fuente, no la textura ni el nombre de la seleccion. Aun
asi, **no llamar `mph` a un velocimetro en km/h**: en el LFQuad3 ese nombre
heredado hizo creer que el reloj estaba en la unidad equivocada, y costo una
ronda. Y comprobar si el arte lleva unidad impresa antes de discutirlo — el de
este quad no lleva ninguna.

## Trampa 5 — el SENTIDO de giro no se deduce, se saca de vanilla

Al montar una aguja hay dos incognitas acopladas: hacia donde apunta el eje y en
que sentido gira el motor con un barrido positivo. Es facil resolver una usando
la otra y creer que se ha demostrado algo; el razonamiento es circular y no
detecta el error.

La regla sale de contenido enviado. Once animaciones de cuadro de cuatro coches
vanilla de 1.29, leidas del ODOL con
`dayz-p3d-debinarizer/scripts/odol_reader.py` (`Animations.classes` para
`angle0/angle1`, `Animations.axis_data[0][i]` para el eje ya resuelto):

| coche | animacion | eje resuelto | angle0 | angle1 | barrido | eje | giro |
|---|---|---|---|---|---|---|---|
| offroadhatchback | IndicatorSpeed | (0, +0.422, +0.907) | 0 | 190 | +190 | hacia | horario |
| offroadhatchback | IndicatorFuel | (0, +0.422, +0.907) | 0 | 90 | +90 | hacia | horario |
| offroadhatchback | IndicatorRPM | (0, +0.422, +0.907) | 20 | 260 | +240 | hacia | horario |
| civiliansedan | IndicatorFuel | (0, -0.458, -0.889) | 40 | -40 | -80 | lejos | horario |
| civiliansedan | IndicatorRPM | (0, -0.458, -0.889) | 50 | -40 | -90 | lejos | horario |
| hatchback_02 | IndicatorFuel | (0, -0.450, -0.893) | 0 | 44 | +44 | lejos | **antihorario** |
| hatchback_02 | IndicatorRPM | (0, -0.316, -0.949) | 0 | -270 | -270 | lejos | horario |
| hatchback_02 | IndicatorSpeed | (0, -0.316, -0.949) | 0 | -270 | -270 | lejos | horario |
| sedan_02 | IndicatorSpeed | (0, +0.371, +0.928) | -127 | 115 | +242 | hacia | horario |
| sedan_02 | IndicatorRPM | (0, -0.371, -0.928) | 125 | -100 | -225 | lejos | horario |
| sedan_02 | IndicatorFuel | (0, -0.371, -0.928) | 44 | -44 | -88 | lejos | horario |

**10 de 11 horarias**, que es como gira el cuadro de cualquier coche. La regla:

> **Barrido positivo sobre un eje que apunta AL CONDUCTOR = horario visto por el.**

En los modelos de vehiculo de DayZ el **+Z es ATRAS** (el salpicadero cae en -Z y
el conductor detras), asi que «apunta al conductor» es `Y>0 y Z>0`. La unica fila
discrepante es un arco de 44 grados de gasolina, que puede estar disenado al
reves a proposito.

Ese 10-de-11 **valida su propia premisa**: si el +Z fuera adelante, la
clasificacion se invertiria entera y saldria 1 de 11 — absurdo para coches
vendidos cuyos cuadros se ven girar horario. No hace falta creerse el convenio
de antemano.

Reproducible en dos minutos sobre
`DZ\vehicles\wheeled\{offroadhatchback,civiliansedan,hatchback_02,sedan_02}\*.p3d`.

En el LFQuad3 este convenio (eje hacia el conductor, `angle0 = reposo - theta(min)`)
es el del cuadro dado por bueno en juego el 2026-09-06. Si un cuadro con esta
regla descansa fuera del cero, el primer sospechoso es el marco (LL-464), no la
regla de vanilla. Comprobacion barata: `light_left` y `light_right` de la Memory
LOD y el signo de `<u_del_marco, light_right - light_left>`; negativo = marco
espejado. LFQuad2 lo confirma por segunda vez, ahora en juego
(2026-09-07 00:15, agente, build `77303210b92d63bd`, ciclo con
`@SurvivorAnims`): velocimetro 0-150 HORARIO, "km/h" legible, rojo a la
DERECHA, aguja en el 0; cuentavueltas 0-6 HORARIO. El 2026-09-06 el
velocimetro iba por debajo del 0 y el cuentavueltas por encima, signo
negado el 4-sep; medido contra los faros, marco ESPEJADO (det +164.81) y
corregido. Las dos lecturas del usuario ("-10", "1000") las predicen
IGUAL el espejo (-13.5 km/h, +880 rpm) y el signo negado: dos
observaciones que no discriminan entre dos modelos no eligen ninguno.
Lo que discrimina es la medida contra los faros. El veredicto del
usuario sobre el build 00:15 nombra otros tres defectos, ninguno del
marco.

## Trampa 6 — la normal cruda de una cara MLOD apunta hacia DENTRO

Corolario de la 5, y es el que muerde al aplicarla. Para clasificar un eje como
«hacia el conductor» es tentador compararlo con la normal de su propia esfera,
calculada como `cross(v1-v0, v2-v0)`. **En MLOD ese cross apunta hacia el
interior del solido**, asi que «el eje esta alineado con la normal» significa que
el eje se mete hacia dentro, no que mire al piloto. Leerlo al reves invierte el
diagnostico completo.

Medido en el LFQuad3: 94-97 % de las caras de los flancos tienen el cross
apuntando hacia dentro.

**El control positivo que lo resuelve, y que vale en cualquier modelo:** elegir
caras cuya direccion exterior no admita discusion —los flancos extremos en X, o
el techo— y comprobar el signo del `dot` entre su cross y esa direccion.

```python
# exterior conocido = +X para el flanco derecho
n = cross(sub(v1, v0), sub(v2, v0))
d = dot(normalizar(n), (1, 0, 0))
# d < 0 en la mayoria de las caras  ->  el cross va hacia DENTRO en este modelo
```

Dos advertencias sobre el control, las dos pagadas:

1. **Elegir bien la cara testigo.** La franja superior del LFQuad3 dio 38 % y no
   concluye: ahi esta el tubo del portaequipajes, con caras mirando a todos
   lados. Los flancos dieron 3 % y 6 % sobre 2.400 caras cada uno. **Un control
   que no discrimina no es un empate: es un control mal elegido**, y contarlo
   como voto empeora el fundamento sin cambiar el resultado.
2. **No usar el punto del piloto como arbitro.** `dot(eje, piloto - pivote)`
   parece intrinseco y no lo es: depende de QUE punto del piloto se tome. En el
   LFQuad3 el cuadro del manillar queda por encima de la pelvis (`crewdriver`
   y=0,964) y por debajo de los ojos, con el pivote a y=1,200 — el signo se
   voltea segun el ancla, +0,142 con la pelvis y -0,994 con el ojo. En un coche
   con salpicadero bajo no pasa; en una moto o un quad, si.

En el LFQuad3 la normal de `<sel>_axis` se ALINEA (no se niega a secas) contra
`n_pilot = (0, 0.82162, 0.57004)`, que apunta al conductor: una negacion
incondicional dependeria del orden de los triangulos del OBJ (`apply_needle_axis`).

## Trampa 7 — `rpm` esta normalizada sobre `rpmMax`, no sobre el numero pintado

`rpm` llega 0..1, y el `1.0` es el final de la `torqueCurve`, **no el ultimo
numero de la esfera**. Si la cara esta pintada 0-6 y el motor llega a 6400, el
«6» cae al `6000/6400 = 93,75 %` del recorrido, y el barrido tiene que ser el
arco pintado dividido por esa fraccion (`x 1,0667`). Pintar 0-6 a arco completo y
cablear como si el techo fuera 6000 hace que **la aguja mienta en todo el
recorrido**, no solo arriba.

Corolario de diseno que conviene decir antes de que el artista cierre el arte:
comparar la **zona roja pintada** con la punta MEDIDA del motor. En el LFQuad3 el
rojo empieza en 5.000 y la punta sostenida son 5.805 rpm (medidas, 404 muestras
con motor encendido), asi que a pleno gas la aguja esta **siempre** dentro del
rojo. Es una decision legitima, pero es una decision.

## Trampa 8 — el arco NO se mide del arte: se propone y se comprueba dibujando

Medir el arco pintado por deteccion automatica parece lo obvio y **fallo cuatro
veces seguidas** sobre un arte limpio, en negro y sin ruido:

1. **Centroide del anillo.** El centroide de un arco parcial no es el centro del
   circulo, asi que iterar centro-anillo-centro DIVERGE. Salio el centro en una
   esquina, con radio mayor que la imagen.
2. **Mayor hueco angular.** Con ticks discretos siempre hay hueco entre marcas;
   el «mayor hueco» acaba siendo uno cualquiera. Peor: la etiqueta central
   (`km/h`, `RPM x1000`) rellena los sectores de abajo y PARTE el hueco real, y
   las marcas rojas de la zona roja desaparecen al pasar a gris (rojo puro =
   luminancia 76, por debajo de cualquier umbral razonable) y FABRICAN un hueco
   donde no lo hay.
3. **Blobs de las etiquetas.** El centroide de `150` no cae al mismo radio ni con
   el mismo sesgo que el de `0`: el ajuste lineal salio con +-8 grados de residuo.
4. **Ticks mayores por profundidad radial.** El recuento no casaba (15 de 16, 9
   de 7) y los pasos salian de 16 a 23 grados en una escala que es regular.

**Lo que si funciona, y es barato:** proponer una escala y **dibujar una aguja
sobre cada valor pintado**. La imagen dice sola si acierta. En el velocimetro las
16 agujas cayeron sobre sus numeros a la primera; en el cuentavueltas el primer
candidato fallo, se corrigio con los dos ticks aislados junto al hueco y a la
segunda cayeron el 0 y el 6 en su sitio.

El instrumento final (`dial_derive_final.py`) deja la asignacion valor<->tick
ESCRITA en `DIALS` y la re-mide con guard (`TOL = 0.5` grados): si un tick se
movio, falla en vez de derivar angulos de otro dibujo. Es la forma auditable de
proponer y comprobar dibujando.

**Y el cierre, que es el unico que no depende de ningun convenio:** rasterizar las
**UV REALES del `.p3d` construido** sobre la textura —muestreando la V como el
motor, `1-v`— y dibujar encima la aguja en `angle0` y en `angle1`. Si los puntos
de UV caen sobre el anillo de ticks y las agujas sobre las marcas extremas, el
mapeo, la textura y los angulos estan bien los tres a la vez. Nada de discos
sinteticos: un render que no lleva las UV que el modelo escribio no prueba nada.
Eso es `dial_gate_final.py`: aguja sobre CADA valor impreso, no solo los
extremos — una recta ajustada a dos extremos pasa por los dos siempre.

## Trampa 9 — una isla de atlas por reloj cuesta la legibilidad

Poner los relojes como islas dentro del atlas del cuerpo tiene dos costes que no
se ven hasta el juego:

- **Resolucion.** La altura de digito es el 2,8-4,5 % del diametro del reloj. Para
  que un digito llegue a 12 px hace falta una isla de 270-430 px. Con islas de 80
  px un digito son 2-4 pixeles: ilegible. Medido desde el asiento, el reloj ocupa
  ~90 px de 1920 en pantalla.
- **La ventana.** Con isla hay que medir centro y radio DENTRO del atlas, que es
  justo la medida que falla (trampa 8).

**Una textura por reloj** quita los dos de golpe: el arte va a resolucion entera y
la ventana UV pasa a ser `[0,1]^2`, sin recorte que medir. Es ademas una
convencion trivial de compartir entre vehiculos. En el LFQuad3: `Dial_kmh`,
`Dial_rpm`, `Dial_fuel` -> `LFQuad3_dial_*_co.paa`, rvmat compartido de gauges
(el contrato pide uno plano propio; ver hallazgo de LFQuad2).

El limite es la PANTALLA, no el atlas. Medido en LFQuad2 (2026-09-07): la
queja "textura pixelada" NO era la textura. El reloj ocupaba 110 px en una
pantalla de 1920 y la textura le daba 501 (4,6 texeles por pixel); un
digito impreso es el 3 % del diametro, o sea 3,3 px, y sale basto por
fuerza. Control: reducir el atlas a 110 px offline reproduce EXACTAMENTE
el aspecto del juego, asi que ni DXT1 ni los mips degradan nada. Subir la
textura no arregla nada; lo que arregla es agrandar el reloj (`R_DIAL`
0.027 -> 0.038, +41 %, 110 -> ~150 px: los numeros se leen) o dibujar
menos numeros y mas grandes. Los ~90 px en pantalla y los 12 px por digito
(arriba) ya lo decian; el sintoma invita a subir la textura, y eso no
cambia nada.

## Trampa 10 — el marco de PANTALLA del conductor, y por que resuelve las dos cosas a la vez

Medido en el LFQuad3 el 2026-09-04 y cerrado el 2026-09-06, tras tres ciclos con
el arte al reves. Las quejas del usuario —«los indicadores estan boca abajo» y
«las agujas no empiezan en el 0»— eran **un solo defecto**, y salen las dos de no
tener un marco declarado. El marco se LEE, no se deduce.

**El marco, anclado al modelo.** El eje de la aguja de la Memory LOD apunta AL
conductor (trampa 6). El "arriba" es +Y del vehiculo proyectado al plano. La
derecha NO es `cross(vista, arriba)` ni "tiene que salir +X": en el LFQuad3 la
derecha del conductor es -X, y el propio fichero lo sabia por los faros. La
derecha se proyecta al plano del reloj desde los marcadores del modelo
(`light_right` menos `light_left`, o `wheel_1_1`/`wheel_2_1`, o un `*_dir`).
Guard `SystemExit` si discrepan (en el LFQuad3 los escribe `memory_lod`; si se
leen de fuera, tambien si faltan). El instrumento
(`dial_derive_final.py`) usa `LIGHT_RIGHT_MINUS_LEFT` y para si esa derecha
coincide con la base vieja `cross(-axis, up)`.

**El objetivo del mapeo, en ese marco:** `derecha -> +U` y `arriba -> -V`. El
menos no es un convenio elegido: V=0 es el borde SUPERIOR de la imagen.

**Como se acredita ese sentido sin creerselo: el control positivo es el propio
modelo.** No hace falta arte de prueba. La carroceria del LFQuad3 escribe
`(u, 1.0 - v)` desde un OBJ (que tiene v=0 abajo), o sea que V=0 es el borde
superior — y esa carroceria lleva ciclos vista en juego sin que nadie diga que
la textura este volteada. Ese es el ancla. En otra cadena (LFQuad2, MLOD de
Arma 2 sin ese `1-v`) el ancla es otra: **se mira que hace el resto del modelo,
no lo que dice esta pagina**. Confirmado en juego el 2026-09-07 00:15
(agente, build `77303210b92d63bd`): arte derecho y legible, horario, rojo
a la derecha. El veredicto del usuario sobre ese build nombra otros tres
defectos, ninguno del marco. Lo que discrimino el espejo previo fue la
medida contra los faros.

**Como se MIDE lo que hay, en vez de discutirlo.** Se ajusta por minimos
cuadrados la matriz 2x2 que lleva (derecha, arriba) a (U, V) usando **las UV
reales del `.p3d` construido**. Con residuo ~1e-6 el ajuste describe el mapeo
entero, y entonces:

| lo que sale | lo que significa |
|---|---|
| `derecha->+U`, `arriba->-V` | correcto |
| `derecha->+U`, `arriba->+V` | **espejo vertical** (el texto se lee como en un espejo) |
| `derecha->-U`, `arriba->-V` | espejo horizontal |
| `derecha->-U`, `arriba->+V` | giro de 180 |

`det > 0` = ESPEJO. Negativo = sin espejo **SOLO si el +U del marco es la
derecha REAL del modelo**. Un +U derivado por producto vectorial sin comprobar
contra los marcadores puede ser la izquierda real (LFQuad3: +X), y entonces el
determinante se lee en un marco espejado y la conclusion se invierte. Medido
con el instrumento anclado sobre los dos builds del LFQuad3: el espejado
(`LFQuad3_body.p3d.pre-mirrorfix-20260906`) da +513 / +491 / +1290 y el
corregido -513 / -491 / -1290; ese MISMO build espejado, medido el 4-sep con el
marco del generador, daba los tres negativos y el cuadro seguia espejado en
juego. El signo solo es evidencia en el marco anclado. Acotar
el ajuste a UN disco: mezclar dos esferas y un swatch da anisotropia 6.9 y
residuo 780 px (LFQuad2); un disco solo, anisotropia 1.000000 y residuo 0.0000
px.

★ Esa tabla es la que distingue un ESPEJO de un GIRO, y hace falta: el usuario
reporto «boca abajo, girar 180» y la medida decia espejo vertical. **No se aplica
la correccion que describe el sintoma: se mapea al objetivo absoluto.** Asi el
resultado es correcto sea cual sea la etiqueta con la que se describio el fallo.

Calibracion del instrumento contra dos estados conocidos (LFQuad3):

| mapeo | base | render | observacion en juego |
|---|---|---|---|
| (+U,+V) | espejada (cross) | boca abajo | build 14:32 del 4-sep: "boca abajo, rotar 180" |
| (+U,-V) | espejada (cross) | espejado, rojo a la IZQUIERDA | build 16:28, visto el 6-sep: "siguen espejadas" |
| (+U,-V) | anclada a los faros | 0 abajo-izq, horario, rojo a la derecha | arreglo; en juego solo el veredicto global del 6-sep |

Los mapeos se nombran en el marco de su `u`: (+U,-V) con la base espejada y
(+U,-V) con la anclada son mapeos DISTINTOS (el HANDOFF del LFQuad3 los llama
(+U,-V) y (-U,-V) en el marco sin voltear). Por eso la base es una columna.

Reproducir los DOS estados conocidos convierte al instrumento en autoridad; uno
solo distingue alcanzable de no alcanzable, no bueno de malo. Hipotesis
descartadas CON su medida: la textura NO llega volteada (diferencia media 0.20
en identidad contra 9.00 en espejo horizontal; rpm 1.80 contra 8.08); el
conductor NO ve la cara trasera del disco (88 caras a +Y contra 16); el eje NO
apunta hacia dentro (`<conductor - p0, axis>` = +0.0210 kmh y +0.0203 rpm); el
winding invertido al binarizar es convencion de formato, no un fallo.

Tres reglas de LL-464:

1. El marco se ANCLA a algo que el artefacto diga de si mismo, no se deduce de
   una convencion de handedness que haya que argumentar.
2. El instrumento no comparte con el codigo la expresion que fija el marco.
3. Se calibra contra estados conocidos antes de creer un veredicto nuevo.

**Y los angulos salen del MISMO marco, por resta.** Con el barrido positivo
horario para el conductor (trampa 5) y horario = angulo de pantalla DECRECIENTE:

```
angle0 = reposo - theta(minValue)
angle1 = reposo - theta(maxValue)
```

donde `reposo` es el angulo de pantalla de la PALA (trampa silenciosa 1 /
`needle_rest`: descarta corona a radio casi constante, banda > 0.97*rmax con
>= 10 puntos repartidos en mas de 90 grados), y `theta(v)` el angulo de
pantalla del valor pintado. Cierre: `dial_gate_final.py` dibuja la aguja sobre
cada valor impreso en el render de las UV reales.

**Por que un espejo mueve el cero.** Bajo el espejo, `theta -> -theta`: el 0
pintado del velocimetro estaba en 213 y se veia en 147, asi que la aguja parada
apuntaba a ~120 km/h. Arreglado el mapeo, el mismo `angle0` cae en el 0. Una
causa, dos sintomas — y por eso no hay que «corregir tambien los angulos» por
separado. Los angulos viejos (-115.1/188.0 y -157.2/86.1) se dedujeron en el
marco espejado: apuntaban a los numeros en su posicion espejada. El barrido se
conservo: el arreglo mueve el origen, no la escala.

## Trampa 11 — no ESTIRES un arte que no es potencia de dos: RELLENALO

El panel de combustible del LFQuad3 es 1536x1024 y la textura tiene que ser potencia
de dos. Se redimensionaba a 2048x1024, o sea un estirado de 1,333 solo en x.

Ese estirado convierte el arco de ticks —un **circulo** en el arte— en una **elipse**.
El circulo ajustado deja de pasar por las marcas, el pivote de la aguja se coloca en un
centro que ya no es el centro, y la aguja pasa por encima de la E y de la F sin tocarlas.

**Rellena con negro a los lados** (el fondo del arte ya suele ser negro) y el arco sigue
siendo un circulo. Las constantes se trasladan solas: `u_2048 = (pad + x_arte) / 2048`.

En el LFQuad3 el panel es un QUAD `Screen` de la pieza 32 elegido por su centroide
(`FUEL_FACE_POS`). `fuel_face_uv` mapea una ventana con la proporcion de la propia
cara centrada en la textura, V = fila/H directamente (sin `1 -`). Pivote y alcance
salen del arco del arte (`FUEL_C_U/V`, `FUEL_R_U`) invirtiendo el mismo mapeo. La
aguja se escala `reach / punta` (`FUEL_INFO["scale"]`; x0.665 en el p3d final:
punta construida 0.01220 / escala 0.82 / punta canonica 0.02239).

★ Corolario general: **un angulo no sobrevive a un mapeo anisotropo.** Antes de usar un
angulo medido en la textura como angulo en pantalla, comprueba que el mapeo es isotropo
—en el ajuste 2x2, `|dU/dderecha|` y `|dV/darriba|` iguales—. Si no lo es, o el angulo
se transforma, o el radio se expresa en las mismas unidades en los dos ejes para que las
dos anisotropias se cancelen.

★ Corolario 2: **la anisotropia se puede absorber en el ARTE**, y suele ser lo barato. Si
la cara ya trae un UV bueno (ventana [0,1] exacta, sin espejo, det negativo) y lo unico que
sobra es que el mapeo no sea isotropo, NO hay que reasignar las UV del modelo anfitrion:
basta componer el arte ya deformado por el factor INVERSO y las dos anisotropias se cancelan
sobre la cara. SUB_BRZ s77: el panel real mide 264.78 x 105.61 mm (2.5072:1) contra una
textura 2:1, asi que el arte se compuso PRE-COMPRIMIDO en horizontal por 0.797711; gate de
isotropia sobre la cara 1.0000 / 1.0053 / 0.9947. Eso evita reasignar las UV de un `.p3d` de
20 MB que no es tuyo: mismo resultado con un orden de magnitud menos de alcance.

Condicion para usarlo: la anisotropia tiene que ser CONSTANTE en la cara (ajuste 2x2 con
residuo ~0; en el SUB_BRZ, 5e-07). Si varia a lo largo de la cara, deformar el arte solo la
cancela en un punto y hay que volver al remapeo.

## Panel de gasolina desde cero

Para un modelo que NO trae cara rectangular donde mapear el arte. El LFQuad3
REUTILIZA un quad `Screen` de la pieza 32 (trampa 11); esa receta no cubre
construir el panel. Numeros del arte oficial `dial_fuel_official.png`
(medido en `assemble_lfquad3.py:140-158` y `convert_textures.py:223-233`).

**Arte y relleno.** El PNG es 1536x1024 y NO es potencia de dos. Se rellena a
2048x1024 con negro y CENTRADO (256 px a cada lado), nunca estirado:
`pad.paste(src_im, ((2048 - src_im.width) // 2, ...)` en
`convert_textures.py:223-233`. Estirar convierte el arco en elipse (trampa 11).

Constantes (`assemble_lfquad3.py:140-158`): FUEL_TEX_W/H 2048/1024,
FUEL_ART_W/H 1536/1024, FUEL_PAD_X 256, FUEL_C_U = (256 + 940)/2048 = 0.58398,
FUEL_C_V = 968.7/1024 = 0.94600 (fila contada desde ARRIBA),
FUEL_R_U = 634.7/2048 = 0.30991 (fraccion del ancho de la textura),
FUEL_E_DEG = 130.0 (marca ROJA del extremo vacio), FUEL_F_DEG = 48.5
(ultimo tick del lleno). Centro y radio salen de un circulo ajustado a los
ticks E..F y COMPROBADO dibujandolo encima (`assemble_lfquad3.py:945-949`),
no de la caja de la cara. Barrido E->F: 81.5 grados, en HORARIO.

**Los mismos numeros en fraccion del arte** (cara que mapea SOLO el arte,
sin bandas de relleno):

- cx = 940/1536 = 0.6120 del ancho
- cy = 968.7/1024 = 0.9460 desde arriba (el pivote queda a 5,4 % del borde
  INFERIOR: es un arco muy abierto)
- r = 634.7/1536 = 0.4132 del ancho de la cara

**Cara y tres ventanas limpias.** En LFQuad3 la cara es un quad `Screen` de
proporcion 1.84:1, elegido por centroide (`FUEL_FACE_POS`,
`assemble_lfquad3.py:164-167`). `fuel_face_uv` (`assemble_lfquad3.py:866-893`)
abre una ventana con la proporcion de la PROPIA CARA centrada en la textura
de 2:1: la ventana ocupa todo el ANCHO de la textura y su alto sale de la
proporcion, asi que con 1.84:1 desborda 44 px por arriba y por abajo (V
fuera de 0..1; se apoya en que el arte es negro ahi y en que el wrap cae
en negro; comentario en `assemble_lfquad3.py:874-878`). V = fila/H
directamente, sin `1 -` (`assemble_lfquad3.py:886-893`).

Consecuencia para una cara NUEVA: con proporcion A la V va de
0.5 - 1/A a 0.5 + 1/A; a 1.5:1 desbordaria 170 px y el wrap traeria a lo
alto de la cara las filas del buje del arte. Por eso NO se copia el mapeo
1.84:1 de LFQuad3. Tres ventanas limpias:

- cara 2:1 (proporcion de la textura rellena): U 0..1, V 0..1; las bandas
  negras de relleno (12,5 % por lado) quedan en la cara; centro y radio,
  los de la TEXTURA (0.58398 / 0.94600 / 0.30991);
- cara 1.5:1 (proporcion del arte): ventana SOLO del arte, U 0.125..0.875,
  V 0..1; sin bandas; centro y radio, los del ARTE (0.6120 / 0.9460 /
  0.4132). Forma rectangular para un pod que no trae cara.
- cara del DIBUJO dentro del arte (medido 2026-09-07, LFQuad2): el arte
  trae su propio borde negro; caja x 305..1742, y 149..875 = 1437x726 px
  = 1.9793:1. Ventana U 0.1489..0.8506 (305/2048 .. 1742/2048), V
  0.1455..0.8545 (149/1024 .. 875/1024); sin bandas ni del relleno ni del
  arte; mapeo esquina a esquina, sin desbordar. Centro y radio referidos
  a la caja del dibujo: cx = 0.6200 del ancho (0.6200 x 1437 + 305 = 1196
  px de textura = 940 px de arte), r = 0.4417 del ancho (0.4417 x 1437 =
  634.7 px). El mismo arco sale por dos reglas distintas (fraccion del
  arte y fraccion del dibujo): es el control cruzado.

En las tres, V = fila/H (sin `1 -`), u = derecha del conductor y w = arriba
del marco ANCLADO (trampas 2 y 10). El arte no se estira ni se espeja.

**Donde cae el pivote.** Con la ventana del dibujo (V hasta 875/1024 =
0.8545) el centro del arco (fila 968.7, V 0.9460) cae POR DEBAJO del
borde inferior de la cara (3,3 mm en el tamano del LFQuad2). Entonces la
aguja no puede ser una aguja desde el buje: LFQuad2 la construyo como
PUNTERO CORTO entre 0.55 y 0.96 del radio del arco; dibujada desde el
pivote asomaria por debajo del panel. Con la ventana del arte entero
(LFQuad3, V hasta 1.0) el pivote queda dentro (V 0.9460) y el buje se ve
pegado al borde inferior.

Un quad basta. En LFQuad3 la cara es del propio pod y no lleva lift; los
discos pintados van a lift 0.0012 (`assemble_lfquad3.py:771`). Para una cara
nueva sobre un pod: el lift que ya usen los discos de ese modelo. LFQuad2
mide +1.89 mm de pala por delante de su disco y le funciona
(medido 2026-09-06, LFQuad2).

**Pivote, empuje, alcance y escala.** El pivote es el centro del arco
invertido por el mismo mapeo de la cara (`assemble_lfquad3.py:955-960`),
mas un empuje de 0.0004 m por delante de la cara a lo largo de su normal
(`assemble_lfquad3.py:963`, "un pelo por delante de la cara, para que no
pelee en z con ella"). El alcance es el radio en metros:
`reach = FUEL_R_U * FUEL_TEX_W * m_per_px` (`assemble_lfquad3.py:961`),
es decir r_fraccion x ancho de la ventana. La aguja canonica
(`canonical_needle`, `assemble_lfquad3.py:972-1035`; trampa 14) se escala
`reach/punta` (`assemble_lfquad3.py:1985-1988`; en LFQuad3 x0.665).

Criterio de la aguja: r_obj = radio maximo en el plano de TODO el objeto;
se DESCARTAN las caras no-Black con algun vertice a r > 0.95 * r_obj, y se
EXIGE que sean exactamente 32 caras OBJ / 64 tris (`SystemExit` si no). Las
piezas de `_shared_parts\gauge_needles\` estan regeneradas con ese corte
desde el 2026-09-07 (censo, arriba: 182 tris, selecciones por radio `hub`
158 / `blade` 24, z >= 0); `canonical_needle` vive en `assemble_lfquad3.py`.

**Angulos: que viaja y que no.** Convenio:
`angle0 = reposo - theta(min)`, `angle1 = reposo - theta(max)`
(`dial_derive_final.py:282`; "El instrumento de derivacion"). Los dos
theta (130.0 y 48.5) y el barrido (81.5) son del ARTE con una ventana
sin estirar ni espejar: viajan. El reposo NO viaja: es la direccion de
la punta de la seleccion `fuel` medida en el p3d CONSTRUIDO, en el marco
anclado (`needle_rest`, `dial_derive_final.py:148`; impreso en
`dial_derive_final.py:232-236`).

En LFQuad3 el reposo de fuel es 0.90 y por eso salen -129.1 / -47.6
(tabla del instrumento). Con la aguja canonica montada con la punta hacia
+u el reposo es ~0: saldria reposo - 130.0 y reposo - 48.5, o sea
-130.0 / -48.5; con otra malla, se mide. LFQuad2 construyo la aguja
apuntando ARRIBA (reposo = 90 en su marco anclado) y le salen angle0
"rad -40.0", angle1 "rad 41.5", barrido +81.5: los theta del arte
(130.0 / 48.5) viajan, el reposo no. Cableado identico al de LFQuad3 y
hueso "fuel" colgando de "drivewheel". Los pares -129.1/-47.6 NO se
copian a otro modelo.

**Cableado.** `generated/model.cfg:238-247` (`IndicatorFuel`, source
"fuel", selection `fuel`, axis `fuel_axis`, memory = 1, minValue 0,
maxValue 1). El hueso cuelga del hueso del salpicadero o del manillar
que corresponda (`skeletonBones[]`: en LFQuad3 `fuel` de `drivewheel`;
contrato de cableado, mas arriba). La geometria nueva del panel Y sus
puntos van en esa seleccion animada (trampa 15); si no, al girar la
pieza el panel se queda atras.

Comprobacion:

- arco dibujado encima del arte (pasa por las marcas E..F)
- V = fila/H, sin `1 -`
- marco anclado (u = derecha del conductor, trampas 2 y 10)
- quiralidad: marco de pieza nueva proyectado del anclado (Gram-Schmidt),
  no reconstruido con cross ni volteado por componentes;
  `<u_pieza, derecha anclada>` > 0 (trampa 2; medido 2026-09-07, LFQuad2)
- donde cae el pivote: dentro de la cara (ventana del arte, V hasta 1.0)
  o debajo (ventana del dibujo, V hasta 0.8545); si cae fuera, puntero
  corto 0.55..0.96 del radio, no aguja desde el buje
- reposo medido en el p3d construido (`needle_rest`); no se hereda
- hueso animado: panel y aguja en la seleccion que gira (trampa 15)
- det negativo en el marco anclado (`det < 0` = directo)

## Trampa 12 — un control de regularidad rechaza una medida mala antes de que te cueste un ciclo

Detectar los ticks del anillo para medir el arco falla de muchas maneras (trampa 8).
Lo que hace la deteccion **usable** no es afinar el umbral: es un control que la propia
escala regala. Una escala de reloj es **regular**, asi que:

- si los ticks detectados no salen equiespaciados dentro de un margen estrecho, la
  deteccion esta mal y **el numero no se usa**;
- el hueco angular MAYOR si es fiable aunque el resto falle: acota el arco.

Medido: sobre el anillo del velocimetro la deteccion daba 46 grupos con pasos de 1,5 a
15,8 grados — control ROJO, numero descartado. Los tres ticks GRANDES, en cambio,
definen el circulo exactamente, y con ese centro los diez ticks del panel de combustible
salieron a 9,0-9,4 grados de paso: control VERDE.

★ Y un umbral de LUMINANCIA se salta los ticks ROJOS (rojo puro = 76, por debajo de
cualquier umbral razonable). El extremo «vacio» de un reloj de combustible es justo una
marca roja: sondea por **color**, no por brillo, o mediras un arco que se queda corto
precisamente en el extremo que define `angle0`. Tinta por canal MAXIMO (`INK = 110`,
`max(r,g,b)`).


## Three silent traps when deriving needle angles (added 2026-09-04, LFQuad3)

All three were found by measuring the built `.p3d`, and each one produced a
plausible number rather than an error.

**1. The needle selection is not only the needle.** Taking "the farthest point of
the needle selection" as the modelled rest direction returned a vertex of the
**hub disc** — a 32-gon at the *same* radius as the printed dial face (measured:
32 points at r=0.0209 with the face at r=0.0208; the blade only reaches 0.0184,
88 % of it). The angle it returned was meaningless and depended on set iteration
order. Discard any ring of points at near-constant radius spread over more than
~90 degrees, then take the farthest of what is left.

**2. Whether the texture is mirrored is a determinant, not a judgement call.**
Fit the affine map (driver-screen x,y) -> (U,V) over the dial faces of the built
model. Image V grows **down** and screen y grows **up**, so an unmirrored texture
gives a **negative** determinant. Positive means mirrored, whatever the numbers
"look like" in a small render. That sign is valid only in a frame whose +right
is the model's real right (LL-464). In LFQuad3 the instrument first shared the
generator's frame (`u = cross(w, axis)`, pointing +X while the driver's right is
-X): on 4-sep it read +512/+491 for the round dials with the (-U,-V) mapping and
-1290 for the fuel panel, and once the mapping went to (+U,-V) it read all three
negative -- on a build that was still mirrored in game. Measured again with the
frame anchored to `light_left`/`light_right`, that same mirrored build reads
+513 / +491 / +1290 and the fixed build -513 / -491 / -1290. The sign became
evidence only once the frame was anchored; the bug was the frame.

  ★ Corollary about evidence (LL-456): two user reports of the same defect are not two
  observations of two states. Check the **build timestamp** before inferring a
  sign from a sequence of reports. Here "upside down" and "mirrored" both
  described the same deployed PBO (14:32); at that moment the intermediate fix
  had not been built yet, and reasoning as if it had produced a sign that the
  render then disproved. The 16:28 build shipped later and was seen on 6-sep
  ("still mirrored"): that is the second calibration point of trap 10, not a
  second observation of the 14:32 build.
  LL-464 amends the ending: that lesson stands, but the sign taken from the
  determinant was measured in a mirrored frame, so the correction that followed
  from it was wrong.

**3. Reading ticks off the art needs two limits and the right ink test.**

- Ink by **max channel**, not luminance. A red tick (255,0,0) is 76 in
  grayscale; an ink threshold of 110 drops the whole redline band and, with it,
  the last major of the scale.
- Measure how far ink reaches inward from the rim, and **stop early**: a hole
  tolerance of ~2 samples and a scan depth of ~0.16 of the radius. With a looser
  tolerance the scan jumps from the tick to the printed number beside it and
  returns 6-10 degree plateaus centred on the numbers, dips and all. Measured on
  this dial a minor tick reaches 0.07-0.11 of the radius and a major 0.15+, which
  separates the two families cleanly. Instrument: `INK = 110`, `KMAX = 160`
  samples at 0.001 r, `holes > 2` cuts, majors with depth >= `MAJOR_MIN = 0.13`.
- Do **not** pick a ring "because it returns as many groups as there are
  majors". A count that matches validates nothing: one ring returned exactly 16
  groups spread over 62 degrees on a dial that sweeps 290.

**And a fit rule when the printed scale is not regular.** The needle rotates
linearly, so a printed scale that is compressed at one end cannot be matched
everywhere. Fit the line to the regular part that is actually used (LFQuad3:
0-100 km/h, residual 1.53 degrees over 11 majors) and let the error fall in the
range the vehicle never reaches, rather than spreading it across the whole face.
Gate it by drawing the needle on **every** printed value, not on the endpoints —
a line fitted to two endpoints passes through both endpoints by construction.
Fuel E and F are NOT re-measured: the depth centroid of those long marks lies 8
degrees off (130.0 and 48.5 come from the arc fit, checked by drawing).

## El instrumento de derivacion

`dial_derive_final.py` lee el `.p3d` YA CONSTRUIDO: los dos puntos de
`<sel>_axis` de la Memory LOD, las UV reales de las caras cuya textura es la
del reloj, y el arte oficial. Auxiliares: `dial_gate_final.py` (render de las
UV reales con el marco anclado, aguja sobre cada valor impreso), `fit_gauge.py`
(ajuste de circulo, ventana y escala; validado contra control positivo),
`needle_draw.py`. `dial_render_v5.py` es anterior al anclaje del marco y no se
usa como cierre.

Numeros finales (medido 2026-09-06, LFQuad3; `dial_angles_final.json`;
`generated/model.cfg`):

| reloj | minValue | maxValue | angle0 | angle1 | barrido | gate |
|---|---|---|---|---|---|---|
| kmh | 0 | 150 | "rad 232.5" | "rad 535.3" | 302.8 | 11 verdes (0..100) |
| rpm | 0 | 1 | "rad 213.1" | "rad 456.4" | 243.3 | 7 verdes (0..6) |
| fuel | 0 | 1 | "rad -129.1" | "rad -47.6" | 81.5 | 3 (E, medio, F) |

Determinantes con el marco anclado: kmh -512.5, rpm -491.2, fuel -1290
(`det < 0` = directo). Tramo de ajuste: velocimetro SOLO 0..100; cuentavueltas
sus 7 mayores; deposito E y F.

Centro y radio de la esfera en la textura (`DIAL_UV`): centro por dos vias que
concuerdan (centroide de lo no-negro y circulo por minimos cuadrados sobre los
mayores, a 12.7 px kmh y 6.4 px rpm); radio = borde REAL del disco (r_max).
Mover el centro MUEVE los angulos: se rederivan cuando cambia. Disco pintado:
32 segmentos, `DISC_R = 0.0254`, centrado en p0 desplazado `lift`, `add_dial_faces`. Cada aguja
con SU disco: `remap_gauge_discs` asigna por x (`aguja_izquierda` en x +0.056 =
velocimetro; `aguja_derecha` en x -0.055 = cuentavueltas; los nombres del OBJ
van al reves de su posicion).

Pila medida a lo largo del eje, en mm desde el ojo: -0.3 el disco pintado con
el `lift` malo de -0.0003 (tapaba todo), +0.0 la pala, +0.8..+2.5 el buje, +1.5
el panel original. Con `lift` 0.0012 el disco pintado va ENTRE la pala y el
panel.

## Trampa 13 — la cache de PAA que no mira el contenido

`convert_textures.py` `emit` se saltaba CUALQUIER `.paa` que existiera en disco,
sin mirar fecha ni contenido. Medido: las caras de reloj empaquetadas eran del
4-sep 03:44 y el arte del 4-sep 15:39; la correccion del cuentavueltas y la
reversion del velocimetro NUNCA llegaron al juego y cada ciclo miraba la
textura vieja. Ahora: sello sha256 del PNG que se le pasa a ImageToPAA,
guardado como `<paa>.src.sha256`; si la fuente cambia, se reconvierte.

La cache NO causaba el espejo, y por un rato lo parecio: dos defectos reales en
el mismo camino, y el primero que aparece no tiene por que ser el que explica
el sintoma.

Los sellos y las copias de seguridad que viven dentro del arbol del mod viajan
en el PBO si el empaquetado copia el arbol entero (95.7 MB en vez de 21.8, con
"Build Successful"); `pack_lfquad3.py` filtra con `ignore_patterns` (LL-467).

## Trampa 14 — un conteo no es una forma: tres agujas de gasolina falsas

La aguja de gasolina del LFQuad3 paso tres veces por las sondas con tres formas
distintas, y ninguna era una aguja (LL-466). Topologia: ver trampa 1.

**Forma 1** (build del 4-sep): filtro por anchura angular vista desde el buje,
corte en 5 grados. Un triangulo de la pala pegado al pivote abarca mucho angulo
POR ESTAR CERCA: el filtro se comio el interior de la hoja y dejo 10 tris de
astilla en la punta (r 0.01122..0.01217). Invisible en juego en el LFQuad3.
ESA es la regla que esta referencia recomendo. Es falsa. La biblioteca
compartida se extrajo con esa regla el 2026-09-03 (7 caras de pala: los dos
octagonos enteros y 5 laterales, sin tapa, pala detras del buje) y se
regenero el 2026-09-07 con `canonical_needle` (censo, arriba). Al revisar a
quien mas las usa, no buscar solo agujas ausentes: en el LFQuad2 la pieza
vieja asoma +1.89 mm delante del disco pintado (otro lift) y se ve.

**Forma 2** (ronda 1 del 2026-09-06, "conservar todo"): el vertice mas lejano
paso a ser uno del disco (0.02544), la escala bajo de x0.665 a x0.585, la pala
quedo al 88 % del arco y el disco entero planto sobre el arco. PASO las sondas
de conteo (182 caras, "del orden de las de kmh") y la revision cruzada. Lo cazo
OTRO observable: el instrumento de derivacion (reposo 0.90 -> 5.63 y 32 puntos
de anillo descartados donde antes habia 0) y el dibujo de la pieza.
`fuel_needle_probe.R1.out`: 182 caras y r_min 0.00111 — verde, y mal.

**Forma 3, comun a las dos:** la pala esta DETRAS del plano del buje (z
negativa) y el pivote solo se adelanta 0.0004 respecto de la cara del panel
(`add_fuel_gauge`): 360 de 546 vertices quedaban detras del panel. Ninguna
sonda media la profundidad hasta que se anadio (`fuel_needle_probe.py`:
"blade vertices behind the panel face (z < -0.0003)" -> OK/HIDDEN).

**Correcta** (`canonical_needle`): r_obj = radio maximo en el plano de todo el
objeto; se DESCARTAN las caras no-Black con algun vertice a r > 0.95 * r_obj, y
se EXIGE que sean exactamente 32 caras OBJ / 64 tris (`SystemExit` si no);
punta = vertice mas lejano de lo que queda; pose canonica (pivote en el origen,
punta +X, eje +Z); z canonica desplazada para que la trasera de la pala quede
en 0. Resultado sobre el p3d final (`fuel_needle_probe.R2.out`): 118 tris
`Gauges` (tapa 30 + octogonos 12 + 76 de quads), punta en r 0.0122 sobre el
arco, 0 vertices detras del panel, reposo 0.90 con 0 puntos de anillo, angulos
-129.1/-47.6 sin cambio.

Cuatro lecciones de LL-466: un conteo no es una forma (pregunta que otra cosa da
ese numero; si es "el objeto entero", el criterio no discrimina); el revisor
hereda el criterio del brief; mide TODAS las dimensiones que el usuario ve (la
profundidad respecto de lo que ocluye); mira la pieza (un dibujo de 60 KB valio
mas que tres rondas de sondas).

## Trampa 15 — la geometria nueva no hereda NINGUNA seleccion

Medido en LFQuad2, build `77303210b92d63bd`, 2026-09-07 00:15. Las 64 caras
de disco pintado anadidas como geometria nueva no estaban en NINGUNA
seleccion; las agujas si (`dial_speed` / `dial_rpm`, que en `skeletonBones`
cuelgan de "drivewheel"). Resultado en juego, literal del usuario: "al girar
la pieza, el dash no gira con ella, los dos circulos quedan atras (las
agujas si rotan)".

Arreglo: meter las caras Y sus puntos en la seleccion animada (`drivewheel`)
en TODOS los LOD que lleven esferas. Build `4034b2e35a9fbb96` (00:33): el
agente ve las esferas girar CON el manillar.

Generalizable: la geometria nueva no hereda ninguna seleccion, y el sintoma
solo aparece al GIRAR; ninguna captura estatica lo delata. Es el simetrico
del caso ya documentado (el disco original que viaja DENTRO de la seleccion
animada y no deberia; tabla de confirmacion, fila LFQuad3): aqui es el que
se queda FUERA y deberia entrar.

Autocomprobacion barata (medido 2026-09-07, LFQuad2): escalar el reloj EN EL
PLANO (no uniforme, para no comerse el margen de la aguja sobre el disco)
no cambia ni las UV (`uv_disco` divide el radio entre `R_DIAL`: cambio
maximo 0.000000 px) ni los angulos (102.55/405.45 y 71.95/315.16 antes y
despues). Si al escalar cambian, el escalado y el mapa no son coherentes.

## Trampa 16 — un manillar con rake separa las manos de los punos al girar

Medido en dos modelos (2026-09-07). El eje `drivewheel_axis` de LFQuad2 estaba 3.4 grados fuera
de la vertical (direccion (0, +0.9982, -0.0599)); a +-30 grados de giro los punos, a 0.378 m del
eje, suben y bajan +-11.5 mm con signo OPUESTO en cada lado (dz +-190 mm es lo dominante, dx
+-41..60). Con el eje EXACTAMENTE vertical ese termino es 0.00 por construccion. Las manos no lo
siguen: en este modelo no hay IK (la Memory LOD solo lleva `crewdriver` y `drivewheel_axis`), la
mano la pone la animacion relativa al asiento. Veredicto del usuario, literal, tras poner el eje
vertical por el mismo punto: "mejor ahora el eje". LFQuad3 lo confirma por el otro lado: su eje
es (0, 1, 0) exacto (Memory LOD, medido en el p3d desplegado `9499be34`), animacion
`drivingwheel` con `angle0 "rad -30"` / `angle1 "rad 30"`, punos a 0.464 m.

Lo que NO era: el barrido. LFQuad3 barre lo mismo (+-30) con los punos MAS lejos (0.464 frente a
0.378 m; 232 mm de vaiven frente a 189) y no tiene el sintoma reportado; si el barrido fuera la
causa, separaria mas al LFQuad3. Queda abierto si las manos siguen a los punos en los TOPES en
LFQuad3 (no desglosado). La postura relativa asiento-puno difiere entre los dos modelos con la
misma animacion: LFQuad2 tiene el manillar 22 cm mas adelante y 12 cm mas abajo respecto al
asiento, y el conductor 16 cm mas alto y 12 cm mas atras respecto a la base del eje.

Estado a las 02:30 del 2026-09-07 (LFQuad2, tras su cierre): barrido a +-22.5 (era +-15) y
conductor 125 mm adelante del original, con el alcance asiento-puno en 588.7 mm, el mismo
que LFQuad3. Contradiccion abierta: LFQuad3 lleva +-30 con 232 mm de vaiven y esta dado
por bueno, asi que si sus manos aguantan eso, el +-30 de LFQuad2 no "sobraba" y la
horquilla del usuario mide otra cosa; hipotesis de LFQuad2: la ALTURA del puno sobre el
asiento (+210 mm en LFQuad3, +118 en LFQuad2). Lo decide mirar las manos de LFQuad3 en los
dos topes (sin hacer).

Regla: el eje del manillar en la Memory LOD se escribe VERTICAL salvo medida que diga lo
contrario, y se comprueba con la direccion del vector, no a ojo (3.4 grados no se ven).

Trampa de metodo al tocar el barrido (LFQuad2, misma noche): el patron `minValue -1 / maxValue
1 / angle0 "rad -30" / angle1 "rad 30"` casa con TRES bloques del `model.cfg`: `drivingwheel` y
las dos ruedas delanteras (`turnfrontleft`, `turnfrontright`, el angulo REAL de direccion). Un
replace por patron deja el quad girando la mitad de lo debido, y en juego se lee como "conduce
raro", no como "el manillar esta mal". Lo caza un assert de unicidad del bloque editado, no un
ojo.

## Trampa 17 — dos signos por cara nueva, los dos copiados de las vecinas

Una cara nueva lleva DOS signos independientes: el winding (orden de vertices: decide el
culling) y la normal ALMACENADA por vertice (decide la iluminacion). Ninguno se deduce de
"tiene que mirar al conductor": los dos se LEEN de las caras vecinas que ya se ven bien y
se comprueban POR SEPARADO. La misma noche (2026-09-07) fallo uno en cada modelo, y en los
dos el otro signo estaba bien:

- **LFQuad2, la normal almacenada.** Winding correcto en las cuatro piezas (`<cross, eje>`
  = -1.000, como los discos), pero panel y aguja de gasolina con la normal almacenada a
  +1.000, escrita "hacia el conductor". De dia se veian igual que las esferas; de NOCHE no
  brillaban con el mismo rvmat. Medido por LFQuad2 sobre su `.p3d`; reproducido aqui con
  otro instrumento sobre el `.p3d` de su PBO desplegado (`3670fe455648c1ac`: 1 + 1 caras
  con `<normal, cross> < 0` en cada LOD visual) y sobre su arbol corregido
  (`5f49257c4380280d`: 0). Su PBO lo lleva desde las 02:10 (`bea1b889b3ecedae`, body
  `5f47e2cbf8ea323f`, 0 con este instrumento); la mirada de NOCHE sigue pendiente.
- **LFQuad3, el winding.** Normal almacenada = cross en todas las caras del cuadro (el
  generador guarda en `add_tri` la `n` del cross): 0 invertidas. Pero `add_fuel_needle`
  forzaba `<cross, axis> > 0` con `axis` hacia el conductor, y TODO lo demas del cuadro
  lleva `<cross, axis> < 0`: discos, coronas, numeros, panel de gasolina y las agujas
  kmh/rpm del OBJ (el cross crudo apunta hacia dentro, trampa 6). 182 tris al reves del
  resto: la aguja de gasolina queda culled desde el asiento en el build `5ac339d3` que se
  dio por bueno (veredicto global; esa aguja no estaba desglosada). Ningun render offline
  lo vio: dibujan las dos caras. Corregido en el generador (la condicion de volteo pasa a
  `> 0`); confirmacion en juego pendiente.

**Regla.** Para cada seleccion nueva del cuadro: `sign(<cross, eje>)` igual al de los
discos ya visibles, y `<normal_almacenada, cross> >= 0` en cada vertice (el suavizado de
60 grados nunca baja de 0.5). Las dos columnas salen de `normal_sign.py` (herramientas de
medida del LFQuad3): agrupa las caras del cuadro por seleccion + textura contra el eje de
Memory mas cercano. Control positivo propio: `--control <sel>` niega en memoria las
normales de una seleccion y todas sus caras deben salir marcadas. Control independiente:
el PBO de LFQuad2 de arriba, que es un defecto real de otra mano. El instrumento da ademas
el veredicto de winding: cada grupo de reloj (selecciones de aguja, texturas de esfera,
numeros y agujas) contra el signo medio de los discos pintados. Los LOD funcionales
(Geometry 1e13, ViewGeometry 6e15, FireGeometry 7e15) quedan fuera salvo `--all-lods`:
llevan 1-2 caras sin textura con la normal a +0.6 que no se renderizan y que un contador
ciego lee como "5 discrepancias" en un modelo limpio (ruido fichado por LFQuad2). Y el
contador de normales solo suma los grupos de reloj: el resto del cluster sale aparte,
informativo, porque los LOD diezmados de un modelo base traen de fabrica alguna cara con
la normal suavizada contra su cross (LFQuad2, LOD 1-3: 5-7 caras cada uno).

**Y en juego, mirar el cuadro tambien de NOCHE** o con la luz del cuadro encendida
(`dashboardMatOn`, el material que `DashboardShineOn` pone sobre `light_dashboard`,
`carscript.c:2481-2497`): el defecto de normal solo asoma con poca luz. El de winding se
ve a cualquier hora, pero solo si se mira ESA pieza: un veredicto global no lo desglosa.

**Y el instrumento de winding tiene un modo de fallo propio: la metrica radial no decide en
una carcasa.** Contar que fraccion de caras tiene el cross apuntando hacia FUERA del
centroide de la malla vale en un solido convexo y no significa nada en una cabina. En el
interior del SUB_BRZ (s77) esa metrica dio **0.0% de caras "hacia el conductor"** y parecia
un modelo entero al reves. No lo era. Una cabina es una carcasa que se mira desde DENTRO y
un cuadro es casi un toro: el centroide cae fuera del material, asi que el radio no es
referencia de nada. El volumen con signo tampoco arbitro: salio negativo en las DOS
variantes, y ninguna de las dos mallas era ESTANCA, condicion sin la cual ese numero
tampoco significa nada.

**Lo que decide es una superficie PLANA que ya se sabe visible, en el MISMO fichero.**
`light_dashboard` (el salpicadero, que obviamente se ve) dio `<cross, eje> = -1.0000` y
`screen_nav` -0.9858; las 100 caras casi paralelas de la aguja nueva llevaban ese mismo
signo. Falsa alarma retirada sin voltear nada: voltear por la metrica radial habria METIDO
el defecto que se creia estar arreglando. Regla: el testigo de winding es una cara vecina
VISIBLE de normal conocida; la estadistica sobre el centroide solo vale en un convexo, y el
volumen con signo solo en una malla estanca, que hay que comprobar ANTES de citarla.

## Receta completa para un cuadro nuevo, en orden

Pasos numerados. Cada uno con su gate offline y la funcion de LFQuad3 que lo
implementa. Otra cadena (LFQuad2 u otra) sigue el orden, no los numeros del
ejemplo.

1. **Anclar el marco.** Derecha = marcadores del modelo proyectados al plano
   del reloj (`light_left`/`light_right`, o equivalente). Guard fatal si
   discrepan (y si faltan, cuando se leen de fuera). Gate: signo de `<u, light_right - light_left>`
   (negativo = marco espejado); el instrumento para si la base vieja y la del
   modelo coinciden. LFQuad3: `MODEL_RIGHT`, `dial_basis`, guard en
   `memory_lod`; `LIGHT_RIGHT_MINUS_LEFT` en `dial_derive_final.py`.
2. **Una textura por reloj**, potencia de dos por relleno (trampa 11), rvmat
   propio plano, fuera de las selecciones de color. Gate: el PAA es del arte
   actual; 0 caras de esfera en `camo1`. LFQuad3: `MAT_TEX` `Dial_*`,
   `convert_textures.py`; el rvmat plano propio es hallazgo de LFQuad2.
3. **Disco pintado + UV polar (+U, -V)** con la base anclada. Gate: `det < 0`
   en CADA disco por separado (trampa 10). LFQuad3: `add_dial_faces`,
   `polar_uv`, `remap_gauge_discs`.
   - **Panel de gasolina.** Si el modelo NO trae cara: seccion
     `## Panel de gasolina desde cero`. Si reutiliza cara: trampa 11
     (`fuel_face_uv`). No copiar el mapeo 1.84:1 de LFQuad3 a una cara nueva.
   - **Seleccion animada** (trampa 15). Meter las caras Y sus puntos (discos,
     panel) en la seleccion del hueso que gira, en TODOS los LOD que lleven
     esferas. Gate: al girar, las esferas viajan con el pod.
4. **Aguja:** pose canonica, pivote = buje Black, solo buje + pala (nunca el
   disco), por delante del panel, disco 1.2 mm detras (`lift = 0.0012`). Gate:
   sonda de profundidad en verde (`z < -0.0003` detras del panel = HIDDEN) y
   DIBUJO de la pieza. LFQuad3: `canonical_needle`, `add_fuel_gauge` (pivote
   0.0004), `needle_parts_probe.py`, `fuel_needle_probe.py`, `needle_draw.py`.
   Gate 2: `normal_sign.py`, winding y normal almacenada de la aguja con el signo de
   los discos (trampa 17): un render sin culling no lo ve.
5. **`<sel>_axis`** = pivote y pivote + normal hacia el conductor; huesos;
   clases Indicator con `"rad"`. Gate: los dos puntos existen en Memory; el
   hueso cuelga del salpicadero. LFQuad3: `apply_needle_axis`, `memory_lod`,
   `generated/model.cfg`.
6. **Angulos con el instrumento:** pares valor<->tick escritos y re-medidos
   (`TOL = 0.5`), ajuste al tramo regular, `angle0 = reposo - theta(min)`, rpm
   sobre `rpmMax`. Gate = aguja sobre CADA valor impreso (`dial_gate_final.py`).
   LFQuad3: `dial_derive_final.py` -> `dial_angles_final.json`.
7. **Cache de texturas por contenido** (`<paa>.src.sha256`) y PBO del tamano
   esperado (los sellos no viajan; trampa 13). LFQuad3: `emit` en
   `convert_textures.py`, `ignore_patterns` en `pack_lfquad3.py`.
8. **Antes de creer un render nuevo**, reproducir dos estados conocidos
   (trampa 10, LL-464). Un solo verde no distingue bueno de malo.
9. **En juego**, mirar: los tres relojes sin espejo y con las caras nuevas; la
   aguja de gasolina visible y entre E y F, y que se mueva con el deposito; con
   el motor encendido, que kmh/rpm se muevan y que la esfera pintada NO gire
   con ellas; que el reposo caiga en el cero. Anotar el veredicto **literal**,
   con build y fecha, y lo que queda sin desglosar. El LFQuad3 se cerro con
   "el dashboard esta bien ya" (2026-09-06, `5ac339d3`); movimiento de fuel,
   disco original y cero exacto siguen sin desglosar. Mirarlo tambien de NOCHE o
   con la luz del cuadro encendida: una normal almacenada invertida solo asoma con
   poca luz, y una pieza culled solo si se mira esa pieza (trampa 17).

## Estado de confirmacion

| | dado por bueno en juego | sin desglosar / abierto |
|---|---|---|
| LFQuad3 | "el dashboard esta bien ya" (2026-09-06, build `5ac339d3`) | movimiento de fuel; disco original en la seleccion animada; cero exacto (gate offline); aguja de gasolina: en `5ac339d3` sus 182 tris llevan el winding al reves del resto del cuadro (culled desde el asiento, medido 2026-09-07, trampa 17), corregido en el generador y SIN confirmar en juego |
| LFQuad2 `77303210b92d63bd` | agente 2026-09-07 00:15, ciclo `@CF` + `@VPPAdminTools` + `@SurvivorAnims`, 1a persona: velocimetro 0-150 HORARIO, "km/h" legible, rojo a la DERECHA, aguja en el 0 impreso; cuentavueltas 0-6 HORARIO, "RPM x1000" legible, rojo a la derecha, aguja en el 0; las dos esferas visibles desde el asiento. Veredicto literal del usuario: "no se ve nada del indicador de gasolina, ademas al girar la pieza, el dash no gira con ella, los dos circulos quedan atras (las agujas si rotan). Por otro lado, como puedes ver, la textura esta pixelada, hay que arreglarlo". LL-464: segunda confirmacion en juego, en otro modelo. Lo que discrimino el espejo previo fue la medida contra los faros (det +164.81). Desplegado como `LFQuad2.pbo` `77303210b92d63bd` + `model.cfg` `1a2df84507870fc8`. | gasolina: no tiene; discos fuera de drivewheel (trampa 15); textura pixelada = limite de pantalla (trampa 9). Ninguno de los tres es del marco. |
| LFQuad2 `4034b2e35a9fbb96` | agente 2026-09-07 00:33 (R 0.038 y discos en drivewheel): las esferas giran CON el manillar; numeros legibles; caras sin espejo; agujas en el 0. Veredicto del usuario: PENDIENTE. | veredicto del usuario pendiente; gasolina: no tiene. |
| LFQuad2 tanda 2 (panel de gasolina + conductor 1 cm adelante; PBO 12.632.912 B; 2026-09-07) | puerta offline verde: UV reales del .p3d rasterizadas contra la textura con el marco anclado a los faros, aguja dibujada en E, 1/2 y F, det -231.92 directo, anisotropia 1.0049, residuo 5.0e-07; desplegado y verificado por contenido dentro del PBO. CONFIRMADO EN JUEGO por el agente (2026-09-07 01:16, ciclo limpio, storage ciclado, personaje nuevo, frame_stale=false): panel visible encima de los relojes, centrado, FUEL / E / 1-2 / F legibles y sin espejo; la aguja construida apuntando ARRIBA (reposo 90) apunta en juego a la F con fuel = 1.0: el motor la giro +41.5 = su angle1. Primera prueba de CABLEADO de la receta, no solo de dibujo. | veredicto del usuario sobre el LFQuad2 en esa ventana: manos y manillar se separan al girar ("el manillar se mueve ligeramente ascendente y la animacion de manos ligeramente descendente"), defecto ajeno al cuadro (eje del manillar con 3.4 grados de rake, en estudio); no consta objecion al panel ni al espejo. |
| SUB_BRZ s77 `AF365A3C` (2026-09-07) | nada: el cliente no se ha lanzado nunca con este build. | TODO el cuadro. Construido offline: tres esferas propias (km/h 0-220, rpm 0-8, gasolina E-F) en `brz_cluster_co.paa` DXT1 2048x1024 sobre las 42 caras de `light_dashboard`, que ya traian ventana UV [0,1] exacta y el swap emisivo nativo `dashboardMatOn/Off`; tres agujas canonicas de 182 tris en los DOS LOD visuales del proxy de interior (1.0 y 1100 = primera persona); `mph` -> `kmh`; `IndicatorSpeed maxValue` 60 -> 220, que era un defecto REAL (la aguja se clavaba a 60 km/h y el resto de la escala estaba muerta). Verificado DENTRO del PBO: el ODOL binarizado del interior lleva `kmh`/`kmh_axis`/`rpm`/`rpm_axis`/`fuel_1`/`fuel_1_axis` y cero `mph`. **El SIGNO del giro es DERIVADO** (mano derecha + el `DrivingWheel` del mismo fichero), no medido: si barre al reves, es un signo. Trampa R7 heredada: el CUERPO (`sub_brz.p3d`, byte a byte igual que antes de s77) conserva puntos de memoria `mph`/`rpm`/`fuel_1` obsoletos con ejes +-Z PUROS frente a los inclinados del interior; `model.cfg` no los referencia, pero el coche #2 puede cablearse al par equivocado. |
