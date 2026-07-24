"""S2: gates INTEG con los scripts de las skills SIN MODIFICAR.

INTEG-INSPECTOR  extract -> build -> extract idempotente (punto fijo)
INTEG-AUDIT      audit_p3d.py pre-migracion sobre modelo sano: ALL PASS
INTEG-VIEWER     p3d_to_gltf.py -> .glb que parsea con pygltflib
RECIPE-COMPAT    extract.py vs P3D.to_dict() semanticamente iguales

Se saltan (con motivo) si el mount de skills o las deps no estan:
    SKILLS_DIR=<...>/skills pytest tests/test_s2_integ.py
"""

import json
import os
import subprocess
import sys

import pytest

from builders import build_multilod_v2_p3d

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.environ.get(
    "SKILLS_DIR", "/sessions/magical-epic-pascal/mnt/.claude/skills")

INSPECTOR = os.path.join(SKILLS, "dayz-p3d-inspector", "scripts")
AUDIT_ORIG = os.path.join(SKILLS, "dayz-p3d-audit", "scripts",
                          "audit_p3d.py")
VIEWER = os.path.join(SKILLS, "dayz-3d-viewer", "scripts",
                      "p3d_to_gltf.py")

needs_skills = pytest.mark.skipif(
    not os.path.isdir(SKILLS), reason="mount de skills no disponible")
def _run(argv, cwd=None):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable] + argv, capture_output=True,
                          text=True, env=env, cwd=cwd or REPO)


def _fixture(fork, tmp_path, name="model.p3d"):
    path = str(tmp_path / name)
    with open(path, "wb") as f:
        build_multilod_v2_p3d(fork).write(f)
    return path


def _semantic_equal(a, b, tol=1e-6, path="$"):
    """Igualdad semantica: floats con tolerancia; wireframe.edges como
    conjunto (el extractor emite orden de iteracion de set)."""
    if path.endswith(".edges"):
        sa = {tuple(e) for e in a}
        sb = {tuple(e) for e in b}
        assert sa == sb, "%s: edges difieren" % path
        return
    if isinstance(a, dict) and isinstance(b, dict):
        assert set(a) == set(b), "%s: claves %r != %r" % (path, set(a),
                                                          set(b))
        for k in a:
            _semantic_equal(a[k], b[k], tol, "%s.%s" % (path, k))
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        assert len(a) == len(b), "%s: len %d != %d" % (path, len(a),
                                                       len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            _semantic_equal(x, y, tol, "%s[%d]" % (path, i))
    elif isinstance(a, float) or isinstance(b, float):
        assert abs(float(a) - float(b)) <= tol, \
            "%s: %r != %r" % (path, a, b)
    else:
        assert a == b, "%s: %r != %r" % (path, a, b)


@needs_skills
def test_integ_inspector_roundtrip_idempotent(fork, tmp_path):
    """INTEG-INSPECTOR: extract->build->extract es punto fijo, exit 0."""
    pytest.importorskip("numpy")
    extract = os.path.join(INSPECTOR, "p3d_inspector_extract.py")
    build = os.path.join(INSPECTOR, "p3d_inspector_build.py")
    model = _fixture(fork, tmp_path)
    r1 = str(tmp_path / "r1.json")
    out1 = str(tmp_path / "out1.p3d")
    r2 = str(tmp_path / "r2.json")
    out2 = str(tmp_path / "out2.p3d")
    r3 = str(tmp_path / "r3.json")

    for argv in ([extract, model, "-o", r1],
                 [build, r1, out1, "--no-autofix"],
                 [extract, out1, "-o", r2],
                 [build, r2, out2, "--no-autofix"],
                 [extract, out2, "-o", r3]):
        r = _run(argv)
        assert r.returncode == 0, (argv, r.stdout, r.stderr)

    with open(r2) as f:
        d2 = json.load(f)
    with open(r3) as f:
        d3 = json.load(f)
    # meta lleva paths distintos por construccion
    d2.pop("meta")
    d3.pop("meta")
    _semantic_equal(d2, d3)


@needs_skills
def test_integ_audit_premigracion_all_pass(fork, tmp_path):
    """INTEG-AUDIT: el audit ORIGINAL de la skill, corriendo sobre el
    fork, da OVERALL ALL PASSED (exit 0) en el modelo sano. (Las
    WARNINGs legacy GeoPhys/autocenter-en-FireGeo son exactamente el
    drift que F2-12 depura; no bloquean.)"""
    model = _fixture(fork, tmp_path)
    r = _run([AUDIT_ORIG, model])
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "OVERALL: ALL PASSED" in r.stdout


@needs_skills
def test_integ_viewer_glb_parses(fork, tmp_path):
    """INTEG-VIEWER: p3d_to_gltf.py (sin modificar) produce un .glb que
    pygltflib parsea con malla no vacia."""
    pytest.importorskip("numpy")
    pygltflib = pytest.importorskip("pygltflib")
    model = _fixture(fork, tmp_path)
    glb = str(tmp_path / "model.glb")
    r = _run([VIEWER, model, glb])
    assert r.returncode == 0, (r.stdout, r.stderr)
    g = pygltflib.GLTF2().load(glb)
    assert g.meshes and g.meshes[0].primitives
    assert g.accessors and g.accessors[0].count > 0


@needs_skills
def test_recipe_compat_extract_vs_to_dict(fork, tmp_path):
    """RECIPE-COMPAT: extract.py y to_dict() son semanticamente iguales
    (schema v1) sobre el mismo fixture."""
    pytest.importorskip("numpy")
    extract = os.path.join(INSPECTOR, "p3d_inspector_extract.py")
    model = _fixture(fork, tmp_path)
    rj = str(tmp_path / "r.json")
    r = _run([extract, model, "-o", rj])
    assert r.returncode == 0, (r.stdout, r.stderr)
    with open(rj) as f:
        d_script = json.load(f)

    with open(model, "rb") as f:
        d_fork = fork.P3D(f).to_dict(source_path=model)
    # via JSON para normalizar tuplas->listas igual que el script
    d_fork = json.loads(json.dumps(d_fork))
    _semantic_equal(d_script, d_fork, tol=1e-9)
