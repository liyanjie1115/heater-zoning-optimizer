import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .config import AnalysisConfig


def default_settings_path() -> Path:
    base = Path.home()
    if "AppData" in str(base):
        root = base / "AppData" / "Local" / "heater-zoning-optimizer"
    else:
        root = base / ".heater-zoning-optimizer"
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.json"


@dataclass
class AppSettings:
    recent_files: List[str] = field(default_factory=list)
    templates: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = None) -> "AppSettings":
        target = path or default_settings_path()
        if not target.exists():
            return cls()
        data = json.loads(target.read_text(encoding="utf-8"))
        return cls(
            recent_files=data.get("recent_files", []),
            templates=data.get("templates", {}),
        )

    def save(self, path: Path = None):
        target = path or default_settings_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "recent_files": self.recent_files,
            "templates": self.templates,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_recent_file(self, file_path: str, limit: int = 8):
        if not file_path:
            return
        recent = [item for item in self.recent_files if item != file_path]
        recent.insert(0, file_path)
        self.recent_files = recent[:limit]

    def save_template(self, name: str, config: AnalysisConfig):
        self.templates[name] = config.to_dict()

    def load_template(self, name: str) -> AnalysisConfig:
        if name not in self.templates:
            raise KeyError(name)
        return AnalysisConfig(**self.templates[name]).validate()
