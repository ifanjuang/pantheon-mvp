#!/usr/bin/env python3
"""Compatibility entrypoint for the packaged Hermes distribution validator."""

from mvp_vertical.hermes_distribution import main


if __name__ == "__main__":
    raise SystemExit(main())
