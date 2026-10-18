from pathlib import Path
from typing import Any, Dict
import yaml


def load_trading_config(path: str = "config/trading_automation.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)["trading_automation"]
