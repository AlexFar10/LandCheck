"""Runs every module on one parcel and collects results in the shared format.

Modules only share the Parcel, so they run independently (and in parallel).
A failing module never breaks the others: it yields an 'Unknown' result with
the error, so the report shows the gap instead of hiding it.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from landcheck.core import ModuleResult, Parcel
from landcheck.modules import ALL


def _run_one(module, parcel: Parcel) -> list[ModuleResult]:
    try:
        return module.run(parcel)
    except Exception as e:  # noqa: BLE001 - surfaced in the result, not swallowed
        return [ModuleResult(risk=r, level="Unknown", value=None, unit=None,
                             confidence="Low", summary="Analysis unavailable",
                             details={"error": f"{type(e).__name__}: {e}"})
                for r in module.RISKS]


def run(parcel: Parcel) -> list[ModuleResult]:
    with ThreadPoolExecutor(max_workers=len(ALL)) as pool:
        batches = pool.map(lambda m: _run_one(m, parcel), ALL)
    return [r for batch in batches for r in batch]


if __name__ == "__main__":
    import json

    from shapely.geometry import box

    from landcheck.core import make_parcel

    demo = make_parcel(box(21.22, 45.75, 21.23, 45.755))  # small plot in Timișoara
    print(json.dumps([r.to_dict() for r in run(demo)], indent=2))
