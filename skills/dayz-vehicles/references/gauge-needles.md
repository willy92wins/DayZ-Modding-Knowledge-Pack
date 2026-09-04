# Agujas y esferas del salpicadero

Medido en el LFQuad3 el 2026-09-03. Cuatro trampas, todas caras, y una pieza
reutilizable para no volver a modelar una aguja.

## La pieza: `_shared_parts/gauge_needles/`

`DayZ Projects\_shared_parts\gauge_needles\` — `needle_large` y `needle_small`,
cada una en `.p3d` (para soltar) y `.obj` (para editar), mas su README.

| | largo | ancho | grosor | tris |
|---|---|---|---|---|
| `needle_large` | 0,02524 m | 0,00571 m | 0,00261 m | 86 |
| `needle_small` | 0,01262 m | 0,00286 m | 0,00130 m | 86 |

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

## Trampa 1 — el objeto que se llama «aguja» no es una aguja

`aguja_derecha` del OBJ del LFQuad3 son **105 caras**, de las cuales **66 son un
disco de 32 gajos** — la cara del reloj — con la aguja encima. Guardarlo entero
mete un reloj en la biblioteca con nombre de aguja.

Y los numeros no lo delatan: la caja del objeto sale `0,0509 x 0,0509 x 0,0026`,
que parece razonable hasta que uno se fija en que 0,0509 es exactamente el
DIAMETRO del disco. **Lo destapo dibujar la silueta**, no medirla.

Separacion barata y robusta: **anchura angular de cada cara vista desde el
buje**. Cada gajo del disco abarca `360/32 = 11,25` grados; la pala de la aguja,
menos de uno. Con un umbral de 5 grados quedan las 39 buenas — aro del buje (32)
y pala (7).

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

**El arreglo es anclar, no compensar:**

```python
w = normalizar(arriba - eje * dot(arriba, eje))   # el "arriba" del vehiculo
u = normalizar(cross(w, eje))                     # derecha, si el eje mira al piloto
u_uv = uc + k * dot(radial, u)
v_uv = vc + k * dot(radial, w)
```

Sin `atan2`: el angulo solo servia para recomponer lo que ya son las dos
coordenadas del punto, y al recomponerlo intercambiaba los ejes.

**El sentido de la V se MIDE en tu propia cadena; no se hereda de aqui.** Lo que se
midio en el LFQuad3: escribiendo la V complementada, el render del atlas reproducia
EXACTAMENTE el espejado que reportaba el usuario; con la V naive el render salia bien
y el juego mal.

> **Acotacion 2026-09-04.** Este parrafo decia antes "porque el motor la invierte al
> muestrear", como si fuera un hecho del motor. No lo es: **el complemento vive en el
> ensamblador**. `assemble_lfquad3.py:1811` hace `uv.append((u, 1.0 - v))` sobre TODA
> UV que toma del OBJ, de modo que la V que acaba en el `.p3d` es `1 - v_obj`, y las
> esferas solo tienen que ser coherentes con ella.
>
> Contramedida de otra sesion sobre el LFQuad2, cuyas UV son del artista de Bohemia en
> un MLOD de Arma 2 y nunca pasan por ese `1-v`: con la V tal cual el arte sale derecho
> y legible, y con `1-v` el modelo muestrea **otra region del atlas**, no un espejo. No
> se contradicen: son cadenas distintas, y el motor solo tiene un convenio.
>
> **La regla operativa no es un signo, es un procedimiento:** la V de las esferas se
> escribe en el MISMO sentido que ya usan las demas UV del modelo, y ese sentido se
> averigua con un **control positivo** -- una pieza de arte cuya orientacion no admita
> discusion (un texto, una pegatina legible), renderizada con las UV reales del `.p3d`.
> Equivocarse produce o un espejo o una traslacion, los dos "plausibles": sin ese ancla
> no se distinguen.
>
> Ninguna de las dos medidas esta confirmada EN JUEGO todavia.

**Instrumento que cierra esto**: rasterizar las caras del reloj del `.p3d` YA
CONSTRUIDO con sus UV reales, muestreando la textura con la V del motor. Eso es
lo que se vera en el juego. Un render sintetico sobre un disco inventado no
vale — no lleva las UV que el modelo escribio.

## Trampa 3 — cambiar el marco INVALIDA `angle0`, y ademas invierte el giro

`angle0` gira la aguja **desde el angulo con el que esta modelada**, no hasta
uno absoluto: `angle0 = cero_pintado - angulo_de_la_malla`, ambos en el mismo
marco.

Desespejar la esfera **mueve el cero pintado a otro sitio fisico**, asi que los
`angle0` viejos dejan de valer aunque nadie haya tocado la aguja. Y como la
relacion entre el marco viejo y el nuevo es una **reflexion**
(`theta_nuevo = C - theta_viejo`), tambien se invierte el sentido de giro: lo
que el motor movia en antihorario pasa a leerse horario.

Como se rederiva sin adivinar:

1. Medir el **arco pintado** en el atlas (los extremos del anillo de ticks).
2. Medir el **angulo de la malla** de la aguja en el marco nuevo, del `.p3d`
   construido: del pivote al vertice mas lejano de la pala.
3. Sacar `C` de un reloj cuyo cero viejo se conozca, y **comprobarla contra el
   otro**. En el LFQuad3: `C = 443` del velocimetro (225 viejo -> 218 medido),
   que predice el cero del cuentavueltas en 290,3 donde el tick extremo medía
   298 — la etiqueta cae por dentro del primer tick, asi que cuadra.

**Ojo con medir el arco por los extremos del anillo**: puede haber ticks de
entrada y salida mas alla de la ultima etiqueta. En el cuentavueltas del LFQuad3
los ticks abarcan 299 grados y la escala impresa 240.

**Si el tope del vehiculo pasa del ultimo numero impreso**, no se estira
`maxValue` dejando los angulos: eso hace que la aguja mienta en todo el
recorrido. Se alarga el barrido en proporcion y se aprovecha el hueco sin
pintar. LFQuad3: 270 grados para 0-120 son 2,25 grados por km/h; con tope 150 el
barrido es 337,5 y los 67,5 de mas caben en los 90 grados de hueco. **Los
numeros impresos siguen siendo verdad a cualquier velocidad.**

## Trampa 4 — la posicion de reserva del eje apunta al reloj equivocado en silencio

Si el codigo escribe una posicion cableada para `<sel>_axis` y luego
`apply_needle_axis` la recalcula, esa reserva no se prueba nunca. Al intercambiar
que aguja mueve que reloj, la reserva se quedo apuntando al otro — y no da error:
si algun dia el calculo no encuentra la aguja, la aguja gira sobre la esfera
equivocada. **Una constante que solo se usa cuando algo falla hay que cambiarla
con lo demas.**

## El contrato de cableado

1. La geometria en una seleccion con nombre propio (p. ej. `kmh`).
2. En la Memory LOD, dos puntos: el pivote y el pivote mas la normal de la
   esfera, con el nombre `<seleccion>_axis`.
3. El hueso en `sections[]` y en el skeleton, colgando del salpicadero.
4. En `CfgModels`:

```
class IndicatorSpeed
{
    type = "rotation";
    source = "speed";        // km/h
    selection = "kmh";
    axis = "kmh_axis";
    memory = 1;
    minValue = 0;
    maxValue = 150;          // el tope REAL del vehiculo
    angle0 = "rad 176.4";    // cero pintado - angulo de la malla
    angle1 = "rad 513.9";    // angle0 + recorrido
};
```

**Todo `angle*` lleva su unidad.** Un numero pelado lo lee el motor en
**radianes** mientras el resto del fichero va en grados: `30` acaba siendo 1718
grados.

**Unidades de las fuentes**: `speed` es **km/h** — `scripts/3_game/vehicles/car.c:113`
declara `proto native float GetSpeedometer()` y
`4_World/classes/useractionscomponent/actions/interact/actiongetouttransport.c:33`
documenta la unidad al comparar contra `GetSpeedometerAbsolute()`. `rpm` viene
normalizada 0..1 sobre `rpmMax`, asi que el recorrido se escala por
`rpmMax / tope_impreso` (LFQuad3: esfera de 240 grados impresa a 8000 con motor
de 6400 -> 192 grados).

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

**Y el cierre, que es el unico que no depende de ningun convenio:** rasterizar las
**UV REALES del `.p3d` construido** sobre la textura —muestreando la V como el
motor, `1-v`— y dibujar encima la aguja en `angle0` y en `angle1`. Si los puntos
de UV caen sobre el anillo de ticks y las agujas sobre las marcas extremas, el
mapeo, la textura y los angulos estan bien los tres a la vez. Nada de discos
sinteticos: un render que no lleva las UV que el modelo escribio no prueba nada.

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
convencion trivial de compartir entre vehiculos.
