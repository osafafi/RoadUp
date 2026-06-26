"""Unit tests for roadup.markings.material."""
from roadup.markings.material import material_key
from roadup.markings.presets import MaterialParams


def test_identical_params_share_a_key() -> None:
    a = MaterialParams(color=(1.0, 0.85, 0.0))
    b = MaterialParams(color=(1.0, 0.85, 0.0))
    assert material_key(a) == material_key(b)


def test_different_color_differs() -> None:
    white = MaterialParams(color=(1.0, 1.0, 1.0))
    yellow = MaterialParams(color=(1.0, 0.85, 0.0))
    assert material_key(white) != material_key(yellow)


def test_float_jitter_below_rounding_collapses() -> None:
    a = MaterialParams(roughness=0.70000001)
    b = MaterialParams(roughness=0.7)
    assert material_key(a) == material_key(b)
