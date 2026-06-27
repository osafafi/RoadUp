"""Root pytest configuration and shared fixtures.

Shared ``@pytest.fixture`` definitions live here so both co-located unit tests and
``tests/integration`` can request them by name.
"""
from __future__ import annotations

import pytest

from roadup.common.types import RoadType
from roadup.geometry.splines import ControlPoint, Spline
from roadup.opendrive.model.network import Header, OpenDriveModel
from roadup.segments.builder import SegmentBuilder


def _line(start, end) -> Spline:
    return Spline(
        points=[ControlPoint(position=start, id="cp_001"), ControlPoint(position=end, id="cp_002")],
        kind="line",
    )


def make_simple_model() -> OpenDriveModel:
    """One straight highway (line) + one drawn bike S-curve (catmullRom). Both editable."""
    highway = (
        SegmentBuilder(RoadType.HIGHWAY)
        .with_reference_line(_line((0.0, 0.0, 0.0), (60.0, 0.0, 0.0)))
        .build("road_001")
    )
    bike = (
        SegmentBuilder(RoadType.BIKE)
        .with_reference_line(
            Spline(
                points=[
                    ControlPoint(position=(0.0, 40.0, 0.0), id="cp_001"),
                    ControlPoint(position=(20.0, 48.0, 0.0), id="cp_002"),
                    ControlPoint(position=(40.0, 40.0, 0.0), id="cp_003"),
                ],
                kind="catmullRom",
            )
        )
        .build("road_002")
    )
    model = OpenDriveModel(header=Header(name="RoadUp Test"))
    model.add_road(highway)
    model.add_road(bike)
    return model


@pytest.fixture
def simple_model() -> OpenDriveModel:
    return make_simple_model()
