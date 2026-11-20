"""Command line entry point: python -m ambilight [--config FILE] [--output null|ws281x] [--input-file FILE]"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

from . import config
from .capture import FileSource, V4L2Capture
from .output import NullOutput, Ws281xOutput
from .pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIGS = (ROOT / "config" / "ambilight.local.toml", ROOT / "config" / "ambilight.example.toml")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ambilight", description="Ambilight pipeline")
    p.add_argument("--config", help="TOML file (default: config/ambilight.local.toml, else the example)")
    p.add_argument("--output", choices=["ws281x", "null"], default="ws281x")
    p.add_argument("--input-file", help="replay raw UYVY frames from this file instead of the grabber")
    p.add_argument("--log-level", default="INFO")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("ambilight")

    path = Path(args.config) if args.config else next(p for p in DEFAULT_CONFIGS if p.exists())
    try:
        cfg = config.load(path)
    except (OSError, config.ConfigError) as exc:
        log.error("cannot load %s: %s", path, exc)
        return 2
    log.info("config: %s", path)

    reg = cfg.regions
    source = (FileSource(args.input_file, reg.frame_width, reg.frame_height) if args.input_file
              else V4L2Capture(cfg))
    output = (NullOutput() if args.output == "null"
              else Ws281xOutput(cfg.layout.count, cfg.leds.gpio_pin, cfg.leds.color_order))

    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    Pipeline(cfg, source, output).run(stop)         # leaves the LEDs off, also on SIGTERM
    log.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
