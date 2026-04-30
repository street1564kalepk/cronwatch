"""CLI entry point for cronwatch daemon."""

import argparse
import logging
import sys

from cronwatch.alerts import AlertDispatcher
from cronwatch.config import load_config
from cronwatch.scheduler import Scheduler
from cronwatch.tracker import JobTracker

logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution times and alert on failures or delays.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="cronwatch.yaml",
        metavar="FILE",
        help="Path to YAML configuration file (default: cronwatch.yaml).",
    )
    parser.add_argument(
        "--poll",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Polling interval in seconds (default: 60).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug-level logging.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("start", help="Start the cronwatch daemon.")
    record = subparsers.add_parser("record", help="Record a job start or finish event.")
    record.add_argument("job", help="Job name as defined in the config.")
    record.add_argument(
        "event",
        choices=["start", "finish"],
        help="Event type to record.",
    )
    record.add_argument(
        "--exit-code",
        type=int,
        default=0,
        help="Exit code for 'finish' events (default: 0).",
    )
    return parser


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=level,
    )


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error("Config file not found: %s", args.config)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load config: %s", exc)
        return 1

    tracker = JobTracker(config.jobs)
    dispatcher = AlertDispatcher(config.alert)
    scheduler = Scheduler(config, tracker, dispatcher)

    if args.command == "start" or args.command is None:
        logger.info("Starting cronwatch daemon (config: %s).", args.config)
        scheduler.run(poll_interval=args.poll)
    else:
        logger.error("Unknown command: %s", args.command)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
