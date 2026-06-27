"""Unit tests for roadup.opendrive.eval.elevation (vertical + lateral profile evaluation)."""
import math

from roadup.geometry.sampling import Frame
from roadup.opendrive.eval.elevation import (
    apply_profiles,
    eval_elevation,
    eval_elevation_slope,
    eval_superelevation,
    vertical_angle_fn,
)
from roadup.opendrive.model.road import ElevationRecord, Road, SuperelevationRecord


def _flat_frame(s: float) -> Frame:
    return Frame(s=s, position=(s, 0.0, 0.0), tangent=(1.0, 0.0, 0.0), normal=(0.0, 1.0, 0.0))


def test_elevation_cubic_and_slope() -> None:
    # z(ds) = 1 + 0.1*ds + 0.01*ds^2 starting at s=10.
    rec = [ElevationRecord(s=10.0, a=1.0, b=0.1, c=0.01)]
    assert math.isclose(eval_elevation(rec, 10.0), 1.0)
    assert math.isclose(eval_elevation(rec, 20.0), 1.0 + 0.1 * 10 + 0.01 * 100)
    assert math.isclose(eval_elevation_slope(rec, 20.0), 0.1 + 2 * 0.01 * 10)


def test_governing_record_is_last_at_or_before_s() -> None:
    recs = [ElevationRecord(s=0.0, a=0.0), ElevationRecord(s=50.0, a=5.0, b=0.0)]
    assert math.isclose(eval_elevation(recs, 49.0), 0.0)
    assert math.isclose(eval_elevation(recs, 50.0), 5.0)
    assert math.isclose(eval_elevation(recs, 80.0), 5.0)


def test_apply_profiles_is_identity_when_flat() -> None:
    road = Road(id="road_001")
    frames = [_flat_frame(0.0), _flat_frame(10.0)]
    assert apply_profiles(frames, road) is frames          # untouched, same object


def test_apply_profiles_lifts_z_and_pitches_tangent() -> None:
    # Constant grade of 5% (b=0.05): z = 0.05*s, tangent pitched by atan(0.05).
    road = Road(id="road_001", elevation=[ElevationRecord(s=0.0, a=0.0, b=0.05)])
    out = apply_profiles([_flat_frame(0.0), _flat_frame(20.0)], road)
    assert math.isclose(out[1].position[2], 0.05 * 20.0)
    pitch = math.atan(0.05)
    assert math.isclose(out[1].tangent[2], math.sin(pitch), abs_tol=1e-9)
    assert math.isclose(math.hypot(*out[1].tangent), 1.0, abs_tol=1e-9)


def test_superelevation_banks_the_normal() -> None:
    # A +0.1 rad bank rolls the left (+t) normal up: normal.z = sin(bank).
    bank = 0.1
    road = Road(id="road_001", superelevation=[SuperelevationRecord(s=0.0, a=bank)])
    out = apply_profiles([_flat_frame(0.0)], road)
    n = out[0].normal
    assert math.isclose(n[2], math.sin(bank), abs_tol=1e-9)
    assert math.isclose(math.hypot(*n), 1.0, abs_tol=1e-9)     # still unit length
    assert math.isclose(eval_superelevation(road.superelevation, 0.0), bank)


def test_vertical_angle_fn_none_when_flat() -> None:
    assert vertical_angle_fn(Road(id="road_001")) is None
    fn = vertical_angle_fn(Road(id="r", elevation=[ElevationRecord(s=0.0, a=0.0, b=0.05)]))
    assert fn is not None
    assert math.isclose(fn(0.0), math.atan(0.05), abs_tol=1e-9)
