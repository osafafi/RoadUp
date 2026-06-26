"""Unit tests for roadup.opendrive.io.userdata."""
import pytest

from roadup.opendrive.io.userdata import USERDATA_NS, decode, encode


def test_namespace() -> None:
    assert USERDATA_NS == "roadup"


def test_encode_is_stable_and_compact() -> None:
    payload = {"b": 2, "a": 1}
    blob = encode(payload)
    # sorted keys, no whitespace
    assert blob == '{"a":1,"b":2}'


def test_roundtrip() -> None:
    payload = {
        "kind": "referenceLine",
        "splineKind": "bezier",
        "controlPoints": [{"id": "cp_001", "pos": [1.0, 2.0, 3.0]}],
    }
    assert decode(encode(payload)) == payload


def test_decode_empty_is_empty_dict() -> None:
    assert decode("") == {}


def test_decode_non_object_raises() -> None:
    with pytest.raises(ValueError):
        decode("[1, 2, 3]")
