"""Configuration storage and environment overrides."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    donor_root: str
    state_root: str
    model_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    model_name: str = "local-model"
    color_mode: str = "auto"
    request_timeout: float = 90.0
    save_history: bool = True
    history_turns: int = 12

    @classmethod
    def defaults(cls) -> "Config":
        home = Path.home()
        return cls(
            donor_root=str(home / "Thrilla-codebases"),
            state_root=str(home / ".thrilla-zilla"),
        )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        config = cls.defaults()
        state_override = os.environ.get("THRILLA_HOME")
        if state_override:
            config.state_root = str(Path(state_override).expanduser())
        config_path = path or (Path(config.state_root) / "config.json")
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            payload = {}
        for field in asdict(config):
            if field in payload:
                setattr(config, field, payload[field])

        # THRILLA_HOME chooses both the config read location and the runtime
        # state location; a stale value inside that file must not override it.
        if state_override:
            config.state_root = str(Path(state_override).expanduser())

        env_map = {
            "THRILLA_DONOR_ROOT": "donor_root",
            "THRILLA_MODEL_URL": "model_url",
            "THRILLA_MODEL": "model_name",
            "THRILLA_COLOR": "color_mode",
        }
        for variable, field in env_map.items():
            if variable in os.environ:
                setattr(config, field, os.environ[variable])
        if config.color_mode not in {"auto", "always", "never"}:
            config.color_mode = "auto"
        try:
            config.request_timeout = float(config.request_timeout)
        except (TypeError, ValueError):
            config.request_timeout = 90.0
        config.request_timeout = min(3600.0, max(1.0, config.request_timeout))
        try:
            config.history_turns = int(config.history_turns)
        except (TypeError, ValueError):
            config.history_turns = 12
        config.history_turns = min(100, max(1, config.history_turns))
        if not isinstance(config.save_history, bool):
            config.save_history = str(config.save_history).lower() in {"1", "true", "yes", "on"}
        config.donor_root = str(config.donor_root)
        config.state_root = str(config.state_root)
        config.model_url = str(config.model_url)
        config.model_name = str(config.model_name)
        return config

    def save(self, path: Optional[Path] = None) -> Path:
        config_path = path or (Path(self.state_root).expanduser() / "config.json")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = config_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(self), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(config_path)
        return config_path

    @property
    def donor_path(self) -> Path:
        return Path(self.donor_root).expanduser()

    @property
    def state_path(self) -> Path:
        return Path(self.state_root).expanduser()
