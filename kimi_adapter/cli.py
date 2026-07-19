"""Command-line entry point for Kimi Adapter."""

from __future__ import annotations

from kimi_adapter.adapter import run_server
from kimi_adapter.config import build_parser, config_from_args


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = config_from_args(args)
    run_server(config)


if __name__ == "__main__":
    main()
