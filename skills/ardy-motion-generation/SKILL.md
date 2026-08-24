---
name: ardy-motion-generation
description: >
  Instalar y operar NVIDIA ARDY — modelo open-source de motion generation en tiempo real
  (autoregressive diffusion, control por texto/waypoints/teclado) — local en WSL2 sobre la
  RTX 3090, con el objetivo de generar locomoción de cuerpo completo (correr, saltar, vaultear,
  scene traversal) para el survivor de DayZ. Usar cuando el usuario pida "instala ARDY", "prueba
  ARDY", "genera animación con ARDY", "motion generation en tiempo real", "locomoción del
  survivor con AI", "animación por texto/waypoints", o retome el proyecto de locomoción DayZ vía
  IA generativa. NO usar esta skill para animación de armas/grip — está fuera de alcance por
  diseño, ver "Qué NO resuelve ARDY" más abajo.
---

# ARDY — motion generation en tiempo real (NVIDIA)

## Qué NO resuelve ARDY (leer antes de invertir tiempo)

El objetivo de esta skill es **locomoción de cuerpo completo del survivor** (correr, saltar,
vaultear, scene traversal), NO animación de armas. El bottleneck real del grip de arma en DayZ
es **parity geométrica** entre el modelo del arma y el `.anm` de referencia sobre
`Weapon_Root`/`RightHand_Dummy` (verificado in-game, proyecto A6_SR2M, 2026-06-17/23) — ARDY
opera sobre un esqueleto de cuerpo completo (~27 huesos "core") con control de manos como
posición de end-effector, sin ningún concepto de geometría de objeto sostenido, dedos
individuales, o el sistema ASI/IK de DayZ. Traer ARDY a un problema de weapon-grip sería
resolver la capa equivocada. Detalle completo y comparación con 6 herramientas más:
`<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md`.

## Qué es (verificado contra research.nvidia.com/labs/sil/projects/ardy/ y
## github.com/nv-tlabs/ardy — no fiar del vídeo/marketing, solo de la fuente primaria)

**ARDY** = "Autoregressive Diffusion with Hybrid Representation for Interactive Human Motion
Generation" (NVIDIA, research lab SIL). Denoiser transformer autoregresivo de dos etapas:
etapa 1 predice root motion global, etapa 2 predice body motion condicionado al root. Soporta
constraints cinemáticos sparse en tiempo/joints. Control en tiempo real: text prompts online,
root trajectories/waypoints, full-body keyframes, end-effector joint positions/rotations, mouse
waypoint editing, keyboard velocity commands, long-horizon goals.

- Repo: https://github.com/nv-tlabs/ardy
- Landing/paper: https://research.nvidia.com/labs/sil/projects/ardy/
- Modelos: https://huggingface.co/collections/nvidia/ardy
- Licencia: Apache-2.0 (código); pesos bajo licencia separada **"NVIDIA Open Model"** — revisar
  términos exactos antes de redistribuir cualquier derivado (no aplica a uso personal de research).

## Presupuesto de VRAM — leer antes de lanzar nada

El text encoder solo (Llama-3-8B-Instruct, bf16) ya pide **~14GB**. El total documentado es
16-18GB mínimo y **~24GB para tiempo real fluido**. La RTX 3090 tiene exactamente 24GB — margen
mucho más ajustado que cualquier modelo ya validado en esta GPU (TRELLIS2-4B, el más pesado
probado hasta ahora, tuvo un peak de solo 6.5GB — ver memoria `trellis2-local-setup`). WSL2 añade
su propio overhead de VRAM encima. Esperar riesgo real de OOM en modo tiempo real.

Mitigaciones a probar en orden si hay OOM:
1. Lanzar `run_text_encoder_server.py` en proceso separado (permite ver su footprint aislado
   antes de sumar el resto del modelo).
2. Cerrar cualquier otro proceso que reserve VRAM (navegador con aceleración GPU, otro modelo
   cargado, etc.) antes de lanzar el demo.
3. Si no cabe fluido: aceptar generación no-tiempo-real (batched/offline) si el repo lo permite
   — no confirmado en el README, comprobar `python scripts/run_demo.py --help` al instalar.

## Setup — WSL2, env conda dedicado

**Usar un env conda NUEVO y SEPARADO, nunca el env `trellis2` existente** — TRELLIS2 fija
PyTorch 2.6.0 exacto con extensiones compiladas contra esa versión build; mezclar dependencias
de dos modelos pesados en el mismo env es la vía más rápida a un entorno roto.

```bash
# Dentro de WSL2 Ubuntu-22.04 (mismo Ubuntu ya usado para TRELLIS2)
conda create -n ardy python=3.11 -y
conda activate ardy

# Instalar PyTorch ANTES que el resto — fijar el índice CUDA a lo que soporte el driver real
# de esta máquina. El repo usa cu126 (CUDA 12.6) como ejemplo; ANTES de copiar el comando tal
# cual, comprobar `nvidia-smi` (driver instalado) contra la matriz de compatibilidad CUDA — no
# asumir que cu126 es correcto sin mirar.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Instalación completa (incluye demo). Alternativas: `pip install -e .` (solo core, sin demo
# interactivo — no sirve para este caso de uso) o `pip install -e ".[trt]"` (con TensorRT).
pip install -e ".[all]"
```

Requisitos de build: **CMake ≥3.15 y compilador C++17**. Confirmar que WSL2 los tiene
(`cmake --version`, `g++ --version`) antes de lanzar el install — si faltan, `sudo apt install
cmake build-essential`.

Clonar el repo en la SSD montada (`/mnt/e/...`, mismo patrón que TRELLIS2), no en la partición
`C:` de WSL2 — más espacio y las cargas de modelos grandes van más rápido. Si `/mnt/e` no está
disponible en esta máquina, confirmar con el usuario dónde clonar antes de decidir por defecto.

### Pesos del modelo — descarga automática, pero requiere gate de HuggingFace

**No hace falta descargar pesos a mano** — el repo los baja automáticamente al usar el demo.
Modelos disponibles: `ARDY-Core-RP-20FPS-Horizon40/8`, `ARDY-G1-RP-25FPS-Horizon52/8`.

El text encoder usa `meta-llama/Meta-Llama-3-8B-Instruct`, que es un modelo **gated** en
HuggingFace — requiere solicitar acceso en su página del modelo (aprobación normalmente rápida
pero no instantánea, dejar margen) y luego autenticar:

```bash
hf auth login
# o, alternativamente, guardar el token directamente:
# echo "hf_..." > ~/.cache/huggingface/token
```

## Lanzar el demo interactivo

```bash
python scripts/run_demo.py
```

Opcional — separar el text encoder en su propio proceso (recomendado aquí para poder vigilar su
footprint de VRAM antes de sumar el resto, dado el margen ajustado de la 3090):

```bash
python scripts/run_text_encoder_server.py
```

UI en el navegador: **http://localhost:2333** (viewer de visualización en **http://localhost:2334**).

**[NO VERIFICADO]** El README no confirma un flag explícito para elegir skeleton `core` vs `g1`
en el propio comando del demo — probablemente se selecciona por config o por qué checkpoint se
carga. Comprobar al instalar (`python scripts/run_demo.py --help`) antes de asumir un flag.

Para locomoción de survivor: usar el skeleton **`core`** (humanoide genérico), NO `g1` — `g1`
es literalmente el rig del robot bípedo real Unitree G1, no un esqueleto de personaje.

## Qué produce (output)

Archivos `.npz` con:
- `posed_joints` — posiciones world-space de joints, shape `[T, J, 3]`
- rotaciones de joint, local y global
- root positions
- foot contacts

El skeleton `g1` exporta además un CSV de MuJoCo qpos (formato de simulación robótica — no
relevante para el caso de uso de locomoción de personaje, ignorar si aparece).

Salidas por defecto van a la carpeta `outputs/` del repo.

## Próximos pasos — integración a DayZ (PLAN, no verificado, no implementar sin gate)

Todo lo de esta sección es diseño, no código probado. Antes de escribir cualquier script de
retargeting, releer `references/dayz-integration-plan.md` (checklist completo) y las dos notas
del vault citadas ahí — no asumir que el pipeline descrito aquí funciona tal cual.

Resumen de la cadena pendiente: `.npz` (world-space joints, esqueleto "core" ~27 huesos) →
importar a Blender → **retarget al `OFP2_ManSkeleton` del player DayZ** (mismo tipo de problema
que ya afronta la skill `mixamo-retarget`, marcada EXPERIMENTAL — esqueleto externo genérico
hacia el esqueleto específico de DayZ, sin mapping oficial de ARDY hacia ningún formato de
videojuego) → exportar `.txa` → pipeline existente de `dayz-animation-pipeline` → `.anm` →
gate in-game.

Ningún tramo de esa cadena está probado. Ver `references/dayz-integration-plan.md` para el
detalle y las preguntas abiertas antes de intentarlo.

## Referencias

- Research y veredicto de aplicabilidad completo (ARDY + 6 herramientas más comparadas):
  `<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md`
- Sistema real de animación DayZ (bones, ASI, skeleton map, grip mechanism verificado in-game):
  `<knowledge-notes>/dayz-animations-creatures-weapons.md`
- Setup WSL2 + GPU pesada ya validado, mismos gotchas de HF-gated models: memoria
  `trellis2-local-setup`
- Plan de integración DayZ (no verificado): `references/dayz-integration-plan.md`
