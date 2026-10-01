from __future__ import annotations

from pathlib import Path

from .models import LifeConfig


def load_life_config(path: str | Path) -> LifeConfig:
    """读取 JSON 配置。"""

    text = Path(path).read_text(encoding="utf-8")
    return LifeConfig.model_validate_json(text)
