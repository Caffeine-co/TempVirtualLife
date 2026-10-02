from __future__ import annotations

from pathlib import Path

from .models import LifeConfig


def load_life_config(path: str | Path) -> LifeConfig:
    """从 JSON 读取并严格校验 LifeConfig。"""

    text = Path(path).read_text(encoding="utf-8")
    return LifeConfig.model_validate_json(text)
