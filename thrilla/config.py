"""Configuration storage and environment overrides."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Optional

from .equipment import normalized_equipment_state
from .limits import DEFAULT_LIMITS


@dataclass
class Config:
    donor_root: str
    state_root: str
    model_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    model_name: str = "local-model"
    owner_name: str = ""
    creator_vault_unlocked: bool = False
    equipment_states: Dict[str, bool] = field(
        default_factory=lambda: normalized_equipment_state({})
    )
    preferred_model_path: str = ""
    runtime_autostart: bool = True
    runtime_context: int = 2048
    runtime_threads: int = 4
    runtime_start_timeout: float = 60.0
    runtime_stop_timeout: float = 5.0
    color_mode: str = "auto"
    request_timeout: float = 180.0
    save_history: bool = True
    history_turns: int = 12
    limit_default_mode: str = "auto"
    limit_modes: Dict[str, str] = field(default_factory=dict)
    limit_values: Dict[str, object] = field(default_factory=dict)

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
        valid_limit_modes = {"on", "auto", "off"}

        if config.limit_default_mode not in valid_limit_modes:
            config.limit_default_mode = "auto"

        if not isinstance(config.limit_modes, dict):
            config.limit_modes = {}
        else:
            config.limit_modes = {
                str(name): mode
                for name, mode in config.limit_modes.items()
                if mode in valid_limit_modes
            }

        if not isinstance(config.limit_values, dict):
            config.limit_values = {}
        else:
            config.limit_values = {
                str(name): value
                for name, value in config.limit_values.items()
            }

        if config.color_mode not in {"auto", "always", "never"}:
            config.color_mode = "auto"
        try:
            config.request_timeout = float(config.request_timeout)
        except (TypeError, ValueError):
            config.request_timeout = 180.0
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
        config.owner_name = str(config.owner_name)
        if not isinstance(config.creator_vault_unlocked, bool):
            config.creator_vault_unlocked = False
        config.equipment_states = normalized_equipment_state(
            config.equipment_states
        )
        config.preferred_model_path = str(config.preferred_model_path)

        if not isinstance(config.runtime_autostart, bool):
            config.runtime_autostart = str(
                config.runtime_autostart
            ).lower() in {"1", "true", "yes", "on"}

        try:
            config.runtime_context = int(config.runtime_context)
        except (TypeError, ValueError):
            config.runtime_context = 2048
        config.runtime_context = min(131072, max(256, config.runtime_context))

        try:
            config.runtime_threads = int(config.runtime_threads)
        except (TypeError, ValueError):
            config.runtime_threads = 4
        config.runtime_threads = min(64, max(1, config.runtime_threads))

        try:
            config.runtime_start_timeout = float(config.runtime_start_timeout)
        except (TypeError, ValueError):
            config.runtime_start_timeout = 60.0
        config.runtime_start_timeout = min(
            600.0, max(1.0, config.runtime_start_timeout)
        )

        try:
            config.runtime_stop_timeout = float(config.runtime_stop_timeout)
        except (TypeError, ValueError):
            config.runtime_stop_timeout = 5.0
        config.runtime_stop_timeout = min(
            60.0, max(0.1, config.runtime_stop_timeout)
        )

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

    def resolve_limit(self, name: str, auto_value: object = None):
        """Resolve one registered limit using stored configuration."""

        mode = self.limit_modes.get(name, self.limit_default_mode)

        legacy_values = {
            "model.request_timeout": self.request_timeout,
            "memory.history_turns": self.history_turns,
            "donor.git_timeout": 4.0,
            "network.remote_model": (
                os.environ.get("THRILLA_ALLOW_REMOTE_MODEL") == "1"
            ),
        }

        has_configured_value = name in self.limit_values

        if has_configured_value:
            configured_value = self.limit_values[name]
        else:
            configured_value = legacy_values.get(name)

        if auto_value is None:
            if has_configured_value:
                auto_value = configured_value
            elif name in legacy_values:
                auto_value = legacy_values[name]

        return DEFAULT_LIMITS.resolve(
            name,
            mode=mode,
            configured_value=configured_value,
            auto_value=auto_value,
        )

    @property
    def donor_path(self) -> Path:
        return Path(self.donor_root).expanduser()

    @property
    def state_path(self) -> Path:
        return Path(self.state_root).expanduser()
