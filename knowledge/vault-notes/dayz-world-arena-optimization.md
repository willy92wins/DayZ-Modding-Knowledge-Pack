# DayZ Enforce — la arena `4_World` y cómo se mide de verdad

> Hub de dominio: qué cobra realmente el compilador de Enforce por módulo, y por
> qué casi todo lo que parece un proxy de tamaño no lo es. Existe porque medir mal
> aquí cuesta campañas enteras: reducir un millón de bytes de fuente puede dar
> **0 kB** de arena.
>
> Medido sobre DayZ `1.29.163451` en un mod de producción con ~1,2 MB de módulo
> World. Los números concretos son de ese mod; **las invariantes y los métodos son
> del motor**. Separar siempre hecho de motor, inferencia y restricción de producto:
> no conviertas una pendiente observada en una constante universal.

## El único veredicto de capacidad

```
candidate.World - empty.World <= limit
```

Un ahorro causal pequeño **no** equivale a PASS de capacidad. Y un PASS nombra el
stack al que pertenece: un par E/candidato donde solo cambia el PBO del producto
mide la contribución absoluta del candidato **en ese snapshot**, no que otro stack
quepa. Usa etiquetas separadas (`PROSPECTIVE_SNAPSHOT_CAPACITY_PASS|FAIL`,
`AFFECTED_STACK_NOT_RUN`) en vez de un PASS ambiguo.

## Jerarquía de evidencia

De mayor a menor autoridad:

1. **Delta de módulo en pares adyacentes de motor** — misma build, stack, orden,
   misión, config y artefactos; Game/World/Mission completos.
2. **Contador engine de clases, calibrado por familia.**
3. **Bytecode semántico retirado de la vista preprocesada servidor** — vale para
   forecast solo cuando el comportamiento desaparece de verdad del módulo.
4. **Declaraciones, métodos, líneas, bytes fuente y tamaño PBO** — son
   inventarios. Por sí solos **no predicen arena**.

## Lo que NO es un proxy (medido)

| Transformación | Cambio estructural | World kB |
|---|---|---:|
| `−16` ficheros, clases iguales | ninguno | `0/−1` |
| `−1.071.376` bytes fuente, clases iguales | ninguno | `−2/0` |
| `−3` clases shell de kit | 3 clases | `1/0` |
| `−1` clase grande, `−19.670` non-whitespace | 1 clase | `44/45` |
| `−12` clases genéricas | 12 unidades | `79/77` |
| `−18` unidades engine | 18 unidades | `101/101` |
| `−3` expresiones genéricas fuente, clases iguales | ninguno | `−3` |
| clases iguales, bytecode servidor real retirado | ninguno | `28/29` |

**El compilador cobra estructura, bytecode y materializaciones, no el texto físico
que las representa.** Un millón de bytes de fuente valió 0 kB; doce clases
genéricas valieron ~78 kB.

## Las invariantes

| # | Invariante | Por qué muerde |
|---|---|---|
| 1 | **Las clases se calibran por familia** | banda observada ~`5,6..6,6 kB` por unidad engine en especializaciones genéricas, pero una clase ordinaria pequeña puede valer **`0 kB`**. Una regresión global de «kB/clase» selecciona el trabajo equivocado |
| 2 | **Expresión genérica retirada ≠ materialización eliminada** | quitar tres `JsonFileLoader<T>` del modelo no bajó el contador engine. El scanner de fuente es precondición, no veredicto |
| 3 | **La masa se cuenta neta** | `cuerpo retirado − fuente exacta de reemplazo − kernels compartidos añadidos`. Un refactor mostró `277.983` caracteres gross y solo `2.700` netos |
| 4 | **El preprocesador servidor cuenta** | una clase entera bajo `#ifndef SERVER` dejó de contarse (`6141→6140`). Analiza con los defines exactos del run; un grep bruto fabrica inventarios falsos |
| 5 | **El contador `classes` incluye tipos generados** | no es un grep de `class`: `203 = 187 declaraciones + 14 genéricos novedosos + 2 residuales`. La resta dimensiona, no bautiza |
| 6 | **Anti-redistribución** | reporta Game, World, Mission **y total**. Un recorte de World que crece igual o más en otro módulo, otro PBO o en runtime no resuelve la presión: la desplaza |
| 7 | **Un PBO no es una arena** | `CfgMods.*ScriptModule.files[]` decide dónde compila un script. Varios PBO que declaran `worldScriptModule` siguen alimentando World: un split de empaquetado con el mismo módulo ahorra **`0 kB`** |
| 8 | **Solo existen cinco keys de ScriptModule** | Engine, GameLib, Game, World, Mission. Un scan de `1.238` `config.cpp` y `1.098` declaraciones `class *ScriptModule` no encontró ninguna key estática custom |

Referencias del motor para la 7: [Modding
Structure](https://community.bistudio.com/wiki/DayZ:Modding_Structure) y [Modding
Basics](https://community.bistudio.com/wiki/DayZ:Modding_Basics).

## La palanca que sí funciona: fachada temprana World → Mission

**Medido, dos pares reproducibles, probe sintético de 200 métodos.** Una clase base
declarada en `4_World` cuyos **cuerpos** viven en una subclase declarada en
`5_Mission` mantiene esa masa fuera de la arena de World.

**No es un truco: es el patrón canónico de vanilla**, y sus cuatro piezas están
repartidas entre los dos módulos exactamente como exige el patrón (verificado en
`P:\scripts` sobre `1.29`):

- `4_world\classes\missionbaseworld.c:3` — la base, **en World**, declara
  `GetRainProcurementHandler()` devolviendo `null`;
- `5_Mission\mission\missionserver.c:822` — el `override` con el cuerpo real,
  **en Mission**;
- `4_World\classes\rainprocurementcomponent.c:14` — el call-site llama por el
  tipo base: `MissionBaseWorld.Cast(g_Game.GetMission()).GetRainProcurementHandler()`;
- `5_Mission\mission\missionbase.c:1` — `class MissionBase extends MissionBaseWorld`
  hereda cruzando módulo.

| | control (cuerpos en World) | candidato (cuerpos en Mission) | movido |
|---|---|---|---|
| World − baseline | +116 / +118 kB | +53 / +54 kB | **+63 / +64 kB (54 %)** |

**Dos matices que deciden si te sirve:**

- **La cáscara no es gratis.** Las firmas siguen declaradas en World: 53 de los 116
  kB se quedaron. El porcentaje movido depende de la proporción cuerpo/firma, así
  que **no se proyecta linealmente entre clases**. El probe tenía 33 % de firmas
  (200 métodos diminutos); una clase de 49 métodos gordos tiene ~4 % y mueve mucho más.
- **Es transporte, no reducción.** Mission sube +103 kB y el overhead de firmas
  duplicadas añade +39 kB. En dos pares con clases reales: World `−139/−140 kB`,
  Mission `+142/+142 kB`, Game `0`, **total `+3/+2 kB`**.

Cuando World está al 97 % y Mission al 39 %, el servidor falla **por capacidad de
módulo** aunque sobre memoria total. Reequilibrar es una solución legítima, pero
llámala **reequilibrio de arena**: no cumple un contrato anti-redistribución.

**Mission es preferible a Game** para un core de World: se compila después y puede
nombrar tipos World; Game se compila antes y no puede.

## El puente dinámico, si no puedes usar la fachada

APIs verificadas en `P:\scripts\1_core\proto\enscript.c`, con la doc del propio
header:

- `Call` (`:139`) — *«The call creates new thread, so it's legal to use
  sleep/wait»*;
- `CallFunction` (`:146`) y `CallFunctionParams` (`:147`) — *«The call do not
  create new thread!!!!»*;
- `LoadScript` (`:160`) — crea un child, pero **no** demuestra arena separada ni
  carga desde VFS/PBO.

Patrón obligatorio: una llamada por **evento grueso** (nunca por getter), nombre de
función fijo no derivado del cliente, resultado comprobado, **fail-closed antes de
cualquier side effect**, warning rate-limited y **cero dispatch en ticks, loops,
scans, timers o callbacks periódicos**.

Diferencia con la fachada: el puente solo admite islas **sin llamadores desde
World**; la fachada es despacho virtual normal y no toca los call-sites.

**Un módulo hijo puede tener su propia arena, pero eso no es ahorro.** El `init.c`
de misión aparece como módulo separado con `1 file`, `1 class`. Si un cambio reduce
World y el coste reaparece en un child que no cuentas, el total de tres módulos
deja de ser completo: es reubicación no contabilizada.

## Método: dos reglas que generalizan fuera de DayZ

**Un experimento de «quitar coste» necesita control positivo.** Un probe de dos
variantes —sin la cosa y con la cosa— produce un **cero ambiguo**: si el candidato
no mueve la métrica, no distingues «el mecanismo funciona» de «el probe no medía
nada» (clase descartada por no referenciada, fichero fuera del módulo, build que no
cogió el cambio). **Tres variantes siempre: baseline / control positivo /
candidato.** El control mete la masa por la vía convencional y **debe** mover la
métrica; si no lo hace, el experimento es `VOID` y el candidato no se lee. Y
**escribe la predicción numérica de las tres filas antes de medir**: un experimento
cuya predicción se redacta después no puede fallar.

**Un piloto mínimo debe poder falsar.** Gate típico: módulos completos, contador
esperado, ahorro World `>=4 kB`, Game/Mission sin crecimiento, ahorro total `>=`
ahorro World, oráculo funcional, stop exacto y cleanup. Y separa siempre los dos
veredictos del piloto: **mecanismo** (World baja, el resto cuadra, el
comportamiento pasa) y **escala** (la densidad medida aplicada a la masa realmente
trasladable alcanza el objetivo con margen). Un mecanismo que da `>=4 kB` no
autoriza escalar.

## Señales de STOP

- El upper depende de borrar comportamiento que luego debe reaparecer en otra clase.
- La propuesta añade loops, scans, timers, callbacks o dispatch para sustituir
  coste estático sin un Intent explícito.
- La familia mezcla clases shell, templates y clases grandes.
- El contador baja pero World no supera la cuantización.
- El ahorro total es menor que el ahorro de World.
- Un hash deriva, o el candidato medido no es el build normal.

## Congelar el stack significa congelar PBOs

Una línea `-mod` prueba orden y raíces, **no** qué PBOs existían dentro de cada
raíz. Para un gate fail-closed la identidad mínima de cada input es: ruta y orden
del mod; conjunto exacto de PBOs bajo esa raíz; tamaño y SHA-256 de cada uno;
digest de su listado de miembros; manifiesto explícito de cero archivos para raíces
vacías; y **el mismo manifiesto antes y después de cada run**. Si falta cualquiera,
escribe `INVENTORY_INCOMPLETE` — nunca lo conviertas en «cero consumers».

**Con `-filePatching`, «mod vacío» significa árbol recursivo vacío.** Comprobar
solo `Addons\*.pbo` no congela un mod: un script suelto, un subdirectorio
inesperado o un reparse point cambia el input efectivo aunque el conteo de PBOs sea
cero.

**Un control positivo distingue «cero hits» de «búsqueda rota».** Al auditar si
alguien externo referencia tus classnames, corre el detector contra un artefacto
que **sí** los contiene. Si el control no encuentra nada, el cero del resto no
significa nada.
