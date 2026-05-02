import os
import tempfile
from pathlib import Path

import pytest

from src.config_loader import load_config, _resolve_env_vars, ConfigError


def test_load_config_loads_settings_and_product():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        config_dir = base / "config"
        config_dir.mkdir()

        (config_dir / "settings.yaml").write_text("""
server:
  host: "0.0.0.0"
  port: 8765
llm:
  api_key: "${TEST_KEY}"
  model: "test-model"
""", encoding="utf-8")
        (config_dir / "product.yaml").write_text("""
product:
  name: "test_card"
  price: 48
""", encoding="utf-8")
        os.environ["TEST_KEY"] = "sk-test123"

        result = load_config(base)
        assert result["settings"]["server"]["host"] == "0.0.0.0"
        assert result["settings"]["server"]["port"] == 8765
        assert result["settings"]["llm"]["api_key"] == "sk-test123"
        assert result["settings"]["llm"]["model"] == "test-model"
        assert result["product"]["product"]["name"] == "test_card"


def test_load_config_raises_on_missing_env():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        config_dir = base / "config"
        config_dir.mkdir()

        (config_dir / "settings.yaml").write_text("""
llm:
  api_key: "${MISSING_KEY}"
""", encoding="utf-8")
        (config_dir / "product.yaml").write_text("""
product:
  name: "test"
""", encoding="utf-8")

        with pytest.raises(ConfigError, match="MISSING_KEY"):
            load_config(base)


def test_resolve_env_vars_replaces_placeholder():
    obj = {"key": "${MY_VAR}", "nested": {"inner": "${OTHER}"}}
    os.environ["MY_VAR"] = "value1"
    os.environ["OTHER"] = "value2"
    missing = _resolve_env_vars(obj)
    assert obj["key"] == "value1"
    assert obj["nested"]["inner"] == "value2"
    assert missing == []


def test_resolve_env_vars_reports_missing():
    if "UNSET_VAR" in os.environ:
        del os.environ["UNSET_VAR"]
    obj = {"key": "${UNSET_VAR}"}
    missing = _resolve_env_vars(obj)
    assert "UNSET_VAR" in missing
