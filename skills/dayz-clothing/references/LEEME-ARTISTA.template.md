# ArmorHneck — modelos worn CORREGIDOS (entrega para ajuste fino)

Fecha: 2026-08-03. Worn models del mod ArmorHneck con las correcciones
estructurales que hacen que la prenda funcione in-game (verificado en DayZ
1.29). El ajuste fino de encaje (brazos, piernas, protector abdominal) queda
pendiente: ese es el encargo de esta entrega.

## Contenido
- `armorhneck_m.fbx` / `armorhneck_f.fbx` — **para trabajar en Blender/Max/Maya**
  (geometria + UVs + PESOS de skinning como vertex groups sobre una armature)
- `armorhneck_beige_co.png` — textura difusa (el FBX la referencia)
- `armorhneck_m.p3d` / `armorhneck_f.p3d` — los mismos modelos en MLOD
  (editables en Object Builder, por si se prefiere esa via)
- `model.cfg` — el model.cfg CORRECTO para binarizar estos modelos

## El FBX
- **Ejes**: Blender estandar, Z arriba, el personaje esta DE PIE mirando +Y.
  Unidades: metros. Origen en los pies del personaje.
- **La armature de 10 huesos es un PORTADOR DE PESOS, no el rig del juego**:
  sus huesos estan colocados en el centroide de cada region solo para que el
  FBX conserve los vertex groups. No sirve para animar. Lo importante son los
  GRUPOS: leftarm, rightarm, leftforearm, rightforearm, leftupleg, rightupleg,
  neck, pelvis, spine, spine3 (en minuscula).
- **Regla de oro**: mover/rotar/esculpir VERTICES para encajar las placas al
  cuerpo. NO renombrar los vertex groups, NO vaciarlos. Se puede repesar si se
  quiere mejorar la deformacion (ver "mejora opcional"), manteniendo suma 1.0
  por vertice y esos mismos nombres de grupo.
- Si se conserva la topologia (mismo numero/orden de vertices), la
  reintegracion al mod es automatica; si se retopa, entregar igualmente el
  FBX con los grupos y lo reconstruimos.

## Que se corrigio ya (NO deshacer)
1. **Orientacion**: la malla original estaba modelada mirando al reves (180
   grados). Estos modelos ya estan en el frame canonico de ropa DayZ
   (en el .p3d: -Z = frente, +X = izquierda anatomica, Y arriba, origen en
   los pies; el FBX ya lo traduce a ejes Blender). Si se re-exporta desde un
   fuente antiguo SIN girar, el bug vuelve.
2. **Esqueleto**: el model.cfg declara `DayzTemporarySkeleton` (159 huesos,
   jerarquia vanilla exacta). Asi se compila TODA la ropa vanilla; con
   `OFP2_ManSkeleton` como nombre el motor NO re-bindea la prenda al jugador
   y se renderiza rigida/flotando. Binarizar SIEMPRE con este model.cfg.
3. Pesos completos y normalizados (suma 1.0 por vertice).

## El encargo (ajuste fino)
Alinear las placas al cuerpo en la pose A canonica de DayZ:
- **Brazos**: hombreras y antebrazos quedan separados/caidos respecto al brazo
  del personaje (el bind canonico tiene los brazos mas horizontales que este
  modelo). Referencia perfecta de "donde debe caer la ropa": el worn de la
  cota de mallas vanilla (`dz\characters\tops\chainmail_m.p3d`).
- **Piernas y protector abdominal**: encaje menor.

## Mejora opcional
El skinning actual es rigido por placa (62% de vertices a un solo hueso, sin
huesos de transicion shoulder/roll/extra/spine1/spine2). Funciona, pero las
articulaciones son toscas en movimiento. Suavizar pesos en las uniones (2-4
influencias, como la ropa vanilla) mejoraria mucho la deformacion.

## Flujo de vuelta
Entregar el FBX (o .blend) modificado. Nosotros lo convertimos a .p3d
(transformacion estandar Blender->DayZ), reconstruimos las selections con los
pesos de los vertex groups, y binarizamos con el model.cfg incluido.
