import importlib.util
import os
import sys

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FORK_ROOT = os.path.dirname(TESTS_DIR)

# El fork manda sobre cualquier py3d de site-packages; tests importables.
sys.path.insert(0, TESTS_DIR)
sys.path.insert(0, FORK_ROOT)


@pytest.fixture(scope="session")
def fork():
    import py3d
    assert getattr(py3d, "IS_DAYZ_FORK", False), (
        "el modulo py3d importado NO es el fork (site-packages interfiere?): %r"
        % getattr(py3d, "__file__", None))
    assert py3d.__version__ == "1.4.0"
    return py3d


def _load_upstream():
    root = os.environ.get("PY3D_UPSTREAM_PATH")
    if not root:
        return None, ("PY3D_UPSTREAM_PATH no establecido - clona "
                      "https://github.com/KoffeinFlummi/py3d y exporta la ruta")
    init = os.path.join(root, "py3d", "__init__.py")
    if not os.path.isfile(init):
        return None, "no existe %s" % init
    spec = importlib.util.spec_from_file_location("py3d_upstream", init)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, None


@pytest.fixture(scope="session")
def upstream():
    """Upstream cargado por ruta (sin pip - D4 CANON). Si no esta disponible,
    los tests CANON se omiten con motivo explicito (suite verde en P:\\ sin red)."""
    mod, why = _load_upstream()
    if mod is None:
        pytest.skip("CANON omitido: " + why)
    assert not getattr(mod, "IS_DAYZ_FORK", False), \
        "PY3D_UPSTREAM_PATH apunta al fork, no a upstream"
    return mod
