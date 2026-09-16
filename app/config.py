import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else ROOT / "config.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def secret(name: str, required: bool = False) -> str | None:
    v = os.environ.get(name, "").strip()
    if required and not v:
        raise RuntimeError(f"missing environment variable / secret: {name}")
    return v or None
