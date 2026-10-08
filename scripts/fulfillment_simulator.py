"""The fictional warehouse: ships paid orders, delivers shipped ones and cancels unpaid ones.

    docker compose exec backend python scripts/fulfillment_simulator.py --once   # one round
    python scripts/fulfillment_simulator.py                                      # every 20 s (the `simulator` service)

Timings come from SIMULATION_*_MINUTES in .env (see app/services/fulfillment_service.py).
"""

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services.fulfillment_service import FulfillmentService


def run_once() -> None:
    with SessionLocal() as db:
        result = FulfillmentService(db).advance(datetime.now(UTC))
    print(f"{datetime.now(UTC):%H:%M:%S} shipped={result.shipped} delivered={result.delivered} cancelled={result.cancelled}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="run one round and stop")
    parser.add_argument("--interval", type=float, default=20.0, help="seconds between rounds")
    args = parser.parse_args()
    configure_logging(get_settings().log_level)
    if args.once:
        run_once()
        return
    while True:
        try:
            run_once()
        except Exception as exc:  # keep going: the database may be restarting
            print(f"simulator round failed: {type(exc).__name__}", flush=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
