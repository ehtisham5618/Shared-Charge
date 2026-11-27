import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared_charge.data import DriverProfile, Request  # noqa: E402

URGENT = dict(private_type="urgent", v=3, w=3, h=1)
FLEX = dict(private_type="flexible", v=2, w=1, h=2)


def driver(did, kind="flexible", strategy="release"):
    return DriverProfile(driver_id=did, strategy=strategy, **(FLEX if kind == "flexible" else URGENT))


def req(did, arrival, departure, kwh, day=1):
    return Request(f"r-{day}-{did}", day, did, arrival, departure, kwh)
