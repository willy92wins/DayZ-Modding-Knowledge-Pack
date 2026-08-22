# Formato de checklist por encuadre

Una entrada es el par `{"q": "<pregunta>", "view": "<encuadre>"}`. El encuadre es el nombre de la imagen contra la que se evalúa esa pregunta, no un hint dentro de una lámina.

## Ejemplo mínimo

```json
[
  {"q": "Are cylindrical parts smooth and round rather than visibly faceted polygons?", "view": "zoom_muzzle__front_iso"},
  {"q": "Is the object sitting on the ground plane rather than floating above it or sunk into it?", "view": "assembled__profile_L"}
]
```

`q` es el texto que ve el modelo y el que se escribe en `answers[].q` del shadow-log.

El token `view` es **sujeto+vista** (`assembled__iso`, `zoom_muzzle__front_iso`), los dos primeros segmentos del fichero `<sujeto>__<vista>__<sujeto>__<version>.png`. No es solo la vista (`iso`, `profile`). Motivo: `profile` existe como vista de `zoom_mag` (`zoom_mag__profile__zoom_mag__v1.png`) y las laterales del conjunto son `profile_L` / `profile_R`. Un token `profile` o `iso` no distingue `assembled__profile_L` de `zoom_mag__profile` (ni `assembled__iso` de `body__iso` / `hg__iso`) y reintroduce el bug original: la pregunta se evaluaría contra el encuadre equivocado.

Este checklist usa cuatro tokens, todos tomados del inventario real (ninguno inventado):

| view | fichero |
|---|---|
| `assembled__iso` | `assembled__iso__assembled__v1.png` |
| `assembled__profile_L` | `assembled__profile_L__assembled__v1.png` |
| `zoom_receiver__right_iso` | `zoom_receiver__right_iso__zoom_receiver__v1.png` |
| `zoom_muzzle__front_iso` | `zoom_muzzle__front_iso__zoom_muzzle__v1.png` |

Asignación de las 8 preguntas (texto intacto): `assembled__iso` para conexiones, huecos, caras invertidas y “¿parece un objeto terminado?”; `zoom_receiver__right_iso` para biseles (primer plano de cantos); `zoom_muzzle__front_iso` para cilindros (cañón); `assembled__profile_L` para proporciones y apoyo en el suelo. Se eligió `profile_L` y no `profile_R`: las dos son laterales del conjunto; hace falta una y L es la que aparece primero en el inventario.

## Cómo pasar varias vistas al CLI

`--view NAME PATH` repetible. `NAME` tiene que coincidir con el `view` de la pregunta. `PATH` es el PNG de ese encuadre. `render` posicional deja de ser obligatorio en `ask` si hay al menos un `--view`.

```
python vr_score.py ask --view assembled__iso assembled__iso__assembled__v1.png --view assembled__profile_L assembled__profile_L__assembled__v1.png --view zoom_receiver__right_iso zoom_receiver__right_iso__zoom_receiver__v1.png --view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png --checklist checks_hardsurface.json
```

Reglas de resolución:

- Sin ningún `--view` (el sweep de `vr_calibrate.py run` sigue siendo esto): todas las preguntas van al PNG posicional en **una** llamada. El campo `view` se registra en la respuesta pero no enruta. Así un checklist ya migrado no tumba `ask foo.png` ni multiplica el coste GPU del calibrador.
- Con `--view`: el nombre es obligatorio. Falta `zoom_muzzle__front_iso` → error, no fallback silencioso. El token `render` es alias del PNG posicional, para checklists mixtos.
- Cada encuadre es una llamada Ollama de **una** imagen. No se mandan las tres vistas en el mismo mensaje.

`--reference` no cambia: sigue siendo la foto/render de comparación, y no es un encuadre más. Su guarda SÍ cambió (SP-266): ya no mira el nombre del modelo sino las dimensiones de las dos imágenes. Dos imágenes del MISMO tamaño en píxeles se colapsan en una sobre `qwen3.x` —y la que sobrevive es impredecible, sigue la caché del prompt—, así que la llamada se rechaza y basta un píxel de diferencia para evitarla. La guarda vieja por nombre de modelo bloqueaba `qwen3.5`, que funciona con tamaños distintos, y dejaba pasar `qwen3.8`, que tiene la misma colisión.

## Alternativa simple descartada

La más simple era no tocar el CLI: un solo PNG (la lámina de tres paneles de siempre) y escribir el encuadre en el prompt (“contesta mirando el primer plano”).

Eso no cubre el caso medido. En EVIDENCIA.md las preguntas 1 y 3 tienen respuesta distinta según el panel de **la misma lámina**, y es exactamente donde los tres modelos discrepan. El diagnóstico es que la unidad de trabajo es (pregunta, imagen), no (pregunta, instrucción sobre una región). Un hint en el prompt sigue enviando los tres paneles juntos.

La otra simple que sí cambia la unidad de trabajo — `ask img0.png img1.png img2.png` y `"view": 2` — cubre una captura de tres archivos en orden fijo. La rompe omitir o reordenar un archivo: el índice 2 deja de ser el zoom del cañón y la pregunta de bisel se evalúa contra otra vista. Es el mismo fallo (pregunta contra el encuadre equivocado), solo que en el argv. `--view zoom_muzzle__front_iso zoom_muzzle__front_iso__zoom_muzzle__v1.png` falla alto si falta ese PNG.

## Retrocompatibilidad y migración

El formato viejo (array plano de cadenas) sigue cargando. Cada cadena es `{q: esa cadena, view: null}` y se puntúa contra el PNG posicional. No hay campo `version`. No hace falta migrar un checklist viejo para que `ask` y `vr_calibrate.py` funcionen.

Para migrar un `.json` viejo: cada string `s` pasa a `{"q": s, "view": "<token>"}`. Elige el encuadre contra el que la pregunta tiene una sola respuesta. No reescribas el texto. Este `checks_hardsurface.json` ya está migrado así.

## Contrato con `vr_calibrate.py`

El calibrador **no** indexa por texto de pregunta. Indexa por:

1. `Path(record["render"]).name` para cruzar con `verdicts.json`
2. posición: `verdicts[name]["answers"][i]` vs `record["answers"][i]["answer"]`

Eso se respeta: `answers` sigue siendo un array en el orden del checklist; cada elemento sigue teniendo `q` (string) y `answer`. Se añaden `view` e `image` (el PNG que realmente se mandó); el calibrador los ignora. `render` del registro sigue siendo el posicional si lo hay, si no el primer PNG de `--view`.

`vr_calibrate.py report` hacía `questions[qi][:60]` asumiendo cadenas. Con objetos eso revienta. Se adaptó solo la carga de etiquetas (`checklist_labels`); el join posicional no se tocó. `run` sigue lanzando `ask <un.png>` sin `--view` (enrutado legado, una imagen). Un barrido multi-vista pediría otra convención de carpeta; no es este cambio.

`checklist_labels` lee el checklist con `encoding="utf-8-sig"`, el mismo motivo que en `vr_score.py`: PowerShell 5.1 escribe BOM y `utf-8` mata el report.

## De dónde sale el `view` de cada pregunta (calibrado 2026-08-16, SP-270)

El campo `view` **no es una opinión**: se mide con el par roto/arreglado del mismo objeto,
que no necesita oro. Se pregunta lo mismo sobre las dos versiones y se miran dos cosas:

- **acierto** contra el oro del objeto, sobre los dos estados;
- **separación** — ¿cambia la respuesta entre roto y arreglado, en las preguntas cuya
  respuesta DEBE cambiar? Un encuadre puede puntuar bien contestando siempre lo mismo.

Medido sobre `mk47_mutant` (8 encuadres, 3 modelos), con el agrupado real de `vr_score.py`:
el checklist saca **77,8% contra un suelo de respuesta constante del 58,3%**, y la pregunta
de conectividad acierta **12/12**.

Tres trampas que costaron una tanda entera y que hay que evitar al re-calibrar:

1. **Con qué preguntas viaja la llamada cambia la respuesta.** La misma pregunta de
   sombreado, misma imagen y mismo modelo: **18/18** en una llamada con otras cuatro de
   sombreado, **9/12** en la llamada con las ocho del checklist. Comparar dos encuadres
   solo vale si el lote se mantiene igual entre ellos. Y no es el TAMAÑO del lote: sacar
   Q5 de `assembled__iso` bajó a Q4 y Q6 dos puntos cada una, con un lote más pequeño.
2. **Un encuadre sin render arreglado no es comparable.** `zoom_muzzle__front_iso` puntúa
   sobre 6 celdas del estado roto en vez de 12, y ahí una respuesta constante saca 6/6.
   Ordenar por porcentaje lo corona con la mitad de la evidencia y cero separación.
3. **Lo que gana en condiciones uniformes puede perder en las reales.** Mover Q1, Q4 y Q5
   juntas a `assembled__profile_R` ganaba en la auditoría y **empeoraba** con el agrupado
   real: Q1 caía de 12/12 a 8/12. Solo se movió Q5, que es la que aguantó la validación.

**Q3 no está mal enrutada: está rota.** «¿Son lisos y redondos los cilindros?» queda al azar
en los ocho encuadres (máximo 50%), porque su redacción permite leer el guardamanos
poligonal —plano por diseño— como un cilindro facetado.

> **RETRACTADO 2026-08-22 — no se arregla reescribiéndola.** Este párrafo cerraba con «se
> arregla reescribiéndola, no moviéndola». Se probó y salió al revés (192 celdas sobre
> `mk47_mutant` + sonda sintética con la verdad puesta por construcción, 2026-08-17):
>
> - **Cuatro redacciones medidas y gana la que ya está** (6/6 y 6/6 en encuadres donde la
>   pieza redonda llena el marco). Umbral numérico 5/6, cláusula de exclusión 5/6, silueta
>   angular 2/6. Sobre el encuadre de objeto completo **las cuatro** caen a 1-2 de 3: el
>   encuadre pesa más que la redacción.
> - **Un umbral dentro del enunciado no se aplica como cuenta**: preguntando «roughly six or
>   fewer sides», los tres modelos dijeron «sí» a la variante de **12** lados.
> - **El agrupado parte la sensibilidad por dos**: 6/6 preguntada sola, 3/6 dentro del lote de
>   ocho que arma `vr_score.py`. Tercera confirmación del efecto lote en esta skill.
> - **El objeto no puede contestarla.** `hg_tube` es un octógono REGULAR y es correcto — la
>   foto de referencia manda sección octogonal (`dossier.md:18,49`). Los cilindros de verdad
>   (`body_brake` 18-22 lados, `body_barrel` 14, `endplate` 24) tienen una sagitta
>   `r*(1-cos(pi/N))` de 0,167-0,213 mm, **menos de 1 px** en cualquiera de los ocho
>   encuadres, contra 1,91 mm y ~6,9 px del octógono. Lo único visiblemente facetado de esta
>   arma es la pieza que debe estarlo.
> - **8 de 12 celdas son falsas alarmas** bajo agrupado real, contra un oro derivado de la
>   geometría. Una pregunta que marca geometría correcta dos tercios de las veces no puede ir
>   en un gate automático, y menos en un pre-filtro que RECHAZA: ahí una falsa alarma tira
>   trabajo bueno. Es el modo de fallo del gate de winding, rojo en el 73 % de lo publicado.
>
> **Qué hacer en su lugar**: sacarla del checklist VLM y de cualquier pre-filtro, y sustituirla
> por un reporte determinista por pieza (lados, radio, desviación, sagitta) que **informe y no
> juzgue** — el problema de Q3 era que exigía adivinar la intención del modelador, y una fila
> «`hg_tube`, 8 lados, r=25,2 mm» devuelve esa decisión a quien puede tomarla. El prototipo
> (`facet_report.py`) todavía **no está en esta skill**.
