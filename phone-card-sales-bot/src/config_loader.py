import os
from pathlib import Path
from typing import Any, Dict, List

import yaml


class ConfigError(ValueError):
    """Raised when configuration is invalid or incomplete."""
    pass


def load_config(base_dir: str | Path = ".") -> Dict[str, Any]:
    """Load settings.yaml and product.yaml, resolving env var placeholders."""
    base = Path(base_dir)
    settings_path = base / "config" / "settings.yaml"
    product_path = base / "config" / "product.yaml"

    with open(settings_path, encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    missing = _resolve_env_vars(settings)
    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Check your .env file."
        )

    with open(product_path, encoding="utf-8") as f:
        product = yaml.safe_load(f)

    return {"settings": settings, "product": product}


def _resolve_env_vars(obj: Any) -> List[str]:
    """Resolve ${VAR_NAME} placeholders. Returns list of missing env vars."""
    missing: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                env_key = v[2:-1]
                value = os.environ.get(env_key)
                if value is None:
                    missing.append(env_key)
                    obj[k] = ""
                else:
                    obj[k] = value
            else:
                missing.extend(_resolve_env_vars(v))
    elif isinstance(obj, list):
        for item in obj:
            missing.extend(_resolve_env_vars(item))
    return missing
