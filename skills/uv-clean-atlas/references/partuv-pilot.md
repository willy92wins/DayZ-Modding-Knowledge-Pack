# PartUV pilot — setup, quirks, measured results (2026-07-16)

PartUV (SIGGRAPH Asia 2025, github.com/EricWang12/PartUV) = PartField hierarchical
part tree + recursive distortion-bounded chart extraction (ABF/LSCM native core,
prebuilt pip wheels). The only 2025-26 "UV AI" with public code + weights.

## Environment that worked (WSL2 Ubuntu 22.04, RTX 3090, miniforge)

```bash
conda create -y -n partuv python=3.11
conda activate partuv
conda install -y -c conda-forge 'libstdcxx-ng>=13' 'libgcc-ng>=13'   # GLIBCXX_3.4.32
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128
pip install torch-scatter -f https://data.pyg.org/whl/torch-2.7.1+cu128.html
cd ~/PartUV && pip install -r requirements.txt && pip install partuv bpy
pip install pytz 'setuptools<81'        # undeclared deps (see quirks)
wget https://huggingface.co/mikaelaangel/partfield-ckpt/resolve/main/model_objaverse.ckpt
```

Run (from the repo root — the checkpoint path is CWD-relative):

```bash
mkdir -p pilot/<mesh_stem>          # quirk: preprocess exports into this subfolder
python demo/partuv_demo.py --mesh_path pilot/<mesh>.obj \
  --output_path pilot/out --pack_method blender --save_visuals
```

## Quirks checklist (each one cost a failed run)

1. `pytz` and `pkg_resources` are undeclared deps → `pip install pytz 'setuptools<81'`
   (setuptools 81+ removed pkg_resources; lightning 2.2 still imports it).
2. Checkpoint integrity: expect **1,243,631,761 bytes**; a truncated download throws
   `PytorchStreamReader failed reading zip archive`. Verify with `zipfile.ZipFile(...).testzip()`.
3. `preprocess()` exports the processed mesh into `<mesh_dir>/<mesh_stem>/` — create
   that folder first or it dies with FileNotFoundError.
4. "Invalid mesh data from numpy arrays. Exiting." (exit 3) = feed it a sanitized
   pure-triangle OBJ: triangulate + dissolve_degenerate + drop loose geometry
   (`scripts/export_objs_tri.py` does exactly this).
5. `export LD_LIBRARY_PATH=$CONDA_PREFIX/lib` before running (native module libstdc++).
6. Distortion threshold is hardcoded `threshold=1.25` in `demo/partuv_demo.py` —
   sed a copy to change it.
7. License caveat: the PartField checkpoint is NVIDIA-derived — review its license
   before shipping outputs in a commercial product (hobby mods: fine in practice).

## Measured results (same meshes, same audit code)

| Config | Islands | Panels | Specks | Density p05–p95 | Notes |
|---|---|---|---|---|---|
| uv-clean-atlas, retopo 10.5k quads | **43** | 28 | 6 | 0.87–1.18 | SAT=0 proven |
| PartUV retopo t=1.25 | 162 | 51 | 108 | 0.85–1.16 | distortion 1.19 |
| PartUV retopo t=2.0 | 127 | 34 | 93 | 0.81–1.20 | distortion 1.80 |
| uv-clean-atlas, rip 36.9k tris | **63** | 23 | 35 | 0.82–1.46 | SAT=0 proven |
| PartUV rip t=1.25 | 232 | 64 | 158 | 0.79–1.25 | distortion 1.25 |

Runtime: PartField inference ~4 s (10–37k tris), full demo ~1.5–2 min incl. model
load and blender packing. VRAM: no issue on a 3090 at these sizes.

Failure mode on vehicle content: PartField splits helicoids (springs) and junk
micro-shells into many parts, each unwrapped to 1–2 charts, with no dust merging —
speck storms. Its packing is `pack_islands` (chaotic orientation).

Reusable idea: PartUV/PartField as an alternative CHART SOURCE (semantic parts)
feeding uv_clean_atlas stages 4–7 (SLIM + guards + SAT + shelf pack) — audit any
such experiment with `scripts/audit_partuv.py`, which imports a PartUV
`final_packed.obj`, scores it, and re-packs it with the semantic shelf packer.
