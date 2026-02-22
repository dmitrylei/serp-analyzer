"""Run keyword schedules in a dedicated process."""

from __future__ import annotations

from serp_monitor.worker.scheduler import run_forever


def main() -> None:
    run_forever()


if __name__ == "__main__":
    main()
