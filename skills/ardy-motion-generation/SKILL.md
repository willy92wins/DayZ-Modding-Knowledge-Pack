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

# ARDY — real-time motion generation (NVIDIA)

## What ARDY does NOT solve (read before investing time)

The goal of this skill is **survivor full-body locomotion** (running, jumping,
vaulting, scene traversal), NOT weapon animation. The actual weapon grip bottleneck in DayZ
is **geometric parity** between the weapon model and the reference `.anm` on
`Weapon_Root`/`RightHand_Dummy` (verified in-game, A6_SR2M project, 2026-06-17/23) — ARDY
operates on a full-body skeleton (~27 "core" bones) with hand control as
end-effector position, without any concept of held object geometry, individual
fingers, or the DayZ ASI/IK system. Bringing ARDY to a weapon-grip problem would be
solving the wrong layer. Full detail and comparison with 6 more tools:
`<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md`.

## What it is (verified against research.nvidia.com/labs/sil/projects/ardy/ and
## github.com/nv-tlabs/ardy — do not trust video/marketing, only primary source)

**ARDY** = "Autoregressive Diffusion with Hybrid Representation for Interactive Human Motion
Generation" (NVIDIA, research lab SIL). Two-stage autoregressive transformer denoiser:
stage 1 predicts global root motion, stage 2 predicts body motion conditioned on root. Supports
sparse kinematic constraints in time/joints. Real-time control: online text prompts,
root trajectories/waypoints, full-body keyframes, end-effector joint positions/rotations, mouse
waypoint editing, keyboard velocity commands, long-horizon goals.

- Repo: https://github.com/nv-tlabs/ardy
- Landing/paper: https://research.nvidia.com/labs/sil/projects/ardy/
- Models: https://huggingface.co/collections/nvidia/ardy
- License: Apache-2.0 (code); weights under separate **"NVIDIA Open Model"** license — review
  exact terms before redistributing any derivative (does not apply to personal research use).

## VRAM budget — read before launching anything

The text encoder alone (Llama-3-8B-Instruct, bf16) already asks for **~14GB**. The documented total is
16-18GB minimum and **~24GB for smooth real time**. The RTX 3090 has exactly 24GB — margin
much tighter than any model already validated on this GPU (TRELLIS2-4B, the heaviest
tested so far, had a peak of only 6.5GB — see `trellis2-local-setup` memory). WSL2 adds
its own VRAM overhead on top. Expect real risk of OOM in real-time mode.

Mitigations to try in order if there is OOM:
1. Launch `run_text_encoder_server.py` in separate process (allows seeing its isolated footprint
   before adding the rest of the model).
2. Close any other process reserving VRAM (browser with GPU acceleration, another loaded
   model, etc.) before launching demo.
3. If it does not fit smoothly: accept non-real-time generation (batched/offline) if the repo allows it
   — not confirmed in README, check `python scripts/run_demo.py --help` upon installing.

## Setup — WSL2, env conda dedicado

**Use a NEW and SEPARATE conda env, never the existing `trellis2` env** — TRELLIS2 pins
exact PyTorch 2.6.0 with extensions compiled against that build version; mixing dependencies
of two heavy models in the same env is the fastest path to a broken environment.

```bash
# Inside WSL2 Ubuntu-22.04 (same Ubuntu already used for TRELLIS2)
conda create -n ardy python=3.11 -y
conda activate ardy

# Install PyTorch BEFORE the rest — pin CUDA index to what the actual driver of this
# machine supports. The repo uses cu126 (CUDA 12.6) as example; BEFORE copying the command as
# is, check `nvidia-smi` (installed driver) against the CUDA compatibility matrix — do not
# assume that cu126 is correct without checking.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Full installation (includes demo). Alternatives: `pip install -e .` (core only, without interactive
# demo — does not work for this use case) or `pip install -e ".[trt]"` (with TensorRT).
pip install -e ".[all]"
```

Build requirements: **CMake ≥3.15 and C++17 compiler**. Confirm that WSL2 has them
(`cmake --version`, `g++ --version`) before launching install — if missing, `sudo apt install
cmake build-essential`.

Clone the repo on the mounted SSD (`/mnt/e/...`, same pattern as TRELLIS2), not on the WSL2
`C:` partition — more space and large model loading goes faster. If `/mnt/e` is not
available on this machine, confirm with the user where to clone before deciding by default.

### Model weights — automatic download, but requires HuggingFace gate

**No need to download weights manually** — the repo downloads them automatically when using the demo.
Available models: `ARDY-Core-RP-20FPS-Horizon40/8`, `ARDY-G1-RP-25FPS-Horizon52/8`.

The text encoder uses `meta-llama/Meta-Llama-3-8B-Instruct`, which is a **gated** model on
HuggingFace — requires requesting access on its model page (approval usually fast
but not instantaneous, allow margin) and then authenticating:

```bash
hf auth login
# o, alternativamente, guardar el token directamente:
# echo "hf_..." > ~/.cache/huggingface/token
```

## Launch the interactive demo

```bash
python scripts/run_demo.py
```

Optional — separate the text encoder into its own process (recommended here to be able to monitor its
VRAM footprint before adding the rest, given the tight margin of the 3090):

```bash
python scripts/run_text_encoder_server.py
```

Browser UI: **http://localhost:2333** (visualization viewer at **http://localhost:2334**).

**[UNVERIFIED]** The README does not confirm an explicit flag to choose skeleton `core` vs `g1`
in the demo command itself — probably selected via config or which checkpoint is
loaded. Check upon installing (`python scripts/run_demo.py --help`) before assuming a flag.

For survivor locomotion: use the **`core`** skeleton (generic humanoid), NOT `g1` — `g1`
is literally the rig of the real Unitree G1 bipedal robot, not a character skeleton.

## What it produces (output)

`.npz` files with:
- `posed_joints` — world-space joint positions, shape `[T, J, 3]`
- joint rotations, local and global
- root positions
- foot contacts

The `g1` skeleton additionally exports a MuJoCo qpos CSV (robotics simulation format — not
relevant for character locomotion use case, ignore if it appears).

Default outputs go to the repo's `outputs/` folder.

## Próximos pasos — integración a DayZ (PLAN, no verificado, no implementar sin gate)

Everything in this section is design, not tested code. Before writing any retargeting
script, re-read `references/dayz-integration-plan.md` (complete checklist) and the two vault
notes cited there — do not assume that the pipeline described here works as-is.

Summary of the pending chain: `.npz` (world-space joints, "core" skeleton ~27 bones) →
import into Blender → **retarget to DayZ player `OFP2_ManSkeleton`** (same type of problem
already faced by `mixamo-retarget` skill, marked EXPERIMENTAL — generic external skeleton
toward specific DayZ skeleton, without official ARDY mapping to any video
game format) → export `.txa` → existing `dayz-animation-pipeline` pipeline → `.anm` →
in-game gate.

No part of that chain is tested. See `references/dayz-integration-plan.md` for
detail and open questions before attempting it.

## Referencias

- Research and full applicability verdict (ARDY + 6 more tools compared):
  `<knowledge-notes>/ai-3d-pipeline/stage-05-animation.md`
- Actual DayZ animation system (bones, ASI, skeleton map, grip mechanism verified in-game):
  `<knowledge-notes>/dayz-animations-creatures-weapons.md`
- WSL2 + heavy GPU setup already validated, same gotchas of HF-gated models: memory
  `trellis2-local-setup`
- DayZ integration plan (unverified): `references/dayz-integration-plan.md`
