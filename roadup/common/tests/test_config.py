"""Unit tests for roadup.common.config."""
from pathlib import Path

from roadup.common.config import (
    PRESETS_DIR_ENV,
    Config,
    load_config,
    resolve_presets_dir,
)


def test_config_defaults() -> None:
    cfg = Config()
    assert cfg.opendrive_version == "1.7"
    assert cfg.default_sampling_step == 1.0
    assert cfg.presets_dir is None


def test_resolve_presets_dir_default_points_at_repo_presets() -> None:
    presets = resolve_presets_dir()
    assert presets.name == "presets"
    # The real presets folder ships with the repo and contains the yaml files.
    assert (presets / "road_types.yaml").is_file()
    assert (presets / "markings.yaml").is_file()


def test_resolve_presets_dir_override_wins(tmp_path: Path) -> None:
    assert resolve_presets_dir(tmp_path) == tmp_path
    assert resolve_presets_dir(str(tmp_path)) == tmp_path


def test_resolve_presets_dir_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(PRESETS_DIR_ENV, str(tmp_path))
    assert resolve_presets_dir() == tmp_path
    # explicit override still beats the env var
    other = tmp_path / "other"
    assert resolve_presets_dir(other) == other


def test_load_config_none_returns_defaults() -> None:
    assert load_config() == Config()


def test_load_config_from_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(
        "default_sampling_step: 0.5\nunknown_key: ignored\n", encoding="utf-8"
    )
    cfg = load_config(str(cfg_file))
    assert cfg.default_sampling_step == 0.5
    assert cfg.opendrive_version == "1.7"  # untouched default
