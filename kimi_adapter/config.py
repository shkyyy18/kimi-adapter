"""Kimi Adapter configuration loader."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml

    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False


@dataclass
class Config:
    """Runtime configuration for the adapter."""

    listen_host: str = "127.0.0.1"
    listen_port: int = 18231
    upstream_host: str = "api.kimi.com"
    upstream_prefix: str = "/coding"
    upstream_scheme: str = "https"
    vscode_watchdog: bool = True
    log_level: str = "INFO"
    silent: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Build a Config from a dictionary, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        """Load config from file or return defaults.

        Order of precedence:
        1. Explicit path argument
        2. KIMI_ADAPTER_CONFIG environment variable
        3. config.yaml / config.yml in working directory
        """
        candidates: list[Path] = []

        if path:
            candidates.append(Path(path))
        else:
            env_path = os.environ.get("KIMI_ADAPTER_CONFIG")
            if env_path:
                candidates.append(Path(env_path))
            candidates.extend([Path("config.yaml"), Path("config.yml")])

        for candidate in candidates:
            if candidate.exists():
                return cls._from_file(candidate)

        return cls()

    @classmethod
    def _from_file(cls, path: Path) -> "Config":
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            if not _HAS_YAML:
                raise RuntimeError(
                    "PyYAML is required to read YAML config files. "
                    "Install with: pip install pyyaml"
                )
            data = yaml.safe_load(text) or {}
        elif suffix == ".json":
            import json

            data = json.loads(text)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")

        return cls.from_dict(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kimi-adapter",
        description="Local proxy adapter for using Claude Code with Kimi backends.",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file (YAML or JSON)."
        " Defaults to config.yaml or KIMI_ADAPTER_CONFIG env var.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Listen host (overrides config file).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Listen port (overrides config file).",
    )
    parser.add_argument(
        "--upstream-host",
        default=None,
        help="Upstream API host (overrides config file).",
    )
    parser.add_argument(
        "--upstream-prefix",
        default=None,
        help="Upstream URL prefix (overrides config file).",
    )
    parser.add_argument(
        "--no-watchdog",
        action="store_true",
        help="Disable VS Code watchdog even if config has it enabled.",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress access logs.",
    )
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    """Build final config by merging file config with CLI overrides."""
    cfg = Config.load(args.config)

    if args.host is not None:
        cfg.listen_host = args.host
    if args.port is not None:
        cfg.listen_port = args.port
    if args.upstream_host is not None:
        cfg.upstream_host = args.upstream_host
    if args.upstream_prefix is not None:
        cfg.upstream_prefix = args.upstream_prefix
    if args.no_watchdog:
        cfg.vscode_watchdog = False
    if args.log_level is not None:
        cfg.log_level = args.log_level
    if args.silent:
        cfg.silent = True

    return cfg
