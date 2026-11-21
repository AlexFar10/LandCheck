from datetime import date

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import box

from landcheck.core import make_parcel, no_coverage, utm_epsg
from landcheck.core import s2
from landcheck import pipeline


def test_utm_zone_romania():
    assert utm_epsg(21.23, 45.75) == 32634   # Timișoara -> zone 34
    assert utm_epsg(28.05, 45.45) == 32635   # Galați -> zone 35


def test_parcel_buffer_and_bbox():
    p = make_parcel(box(21.22, 45.75, 21.23, 45.755), buffer_m=500)
    assert p.epsg == 32634
    w, s, e, n = p.bbox_wgs84
    assert w < 21.22 and e > 21.23 and s < 45.75 and n > 45.755   # buffer grows the box
    assert 30 < p.parcel_area_ha < 50                             # ~780 m x 555 m


def test_invalid_parcel():
    from shapely.geometry import Polygon
    with pytest.raises(ValueError):
        make_parcel(Polygon())


def test_no_coverage_is_unknown_not_low():
    r = no_coverage("ground_stability", "no EGMS points")
    assert r.level == "Unknown" and r.to_dict()["value"] is None


def _fake_ds():
    t = pd.to_datetime(["2021-06-01", "2023-06-01"])
    red = xr.DataArray(np.full((2, 2, 2), 1500.0), dims=("time", "y", "x"), coords={"time": t})
    scl = xr.DataArray(np.array([[[4, 4], [4, 9]], [[4, 4], [4, 4]]]), dims=("time", "y", "x"),
                       coords={"time": t})
    return xr.Dataset({"red": red, "scl": scl})


def test_offset_applied_per_date():
    ds = s2.to_reflectance(_fake_ds(), {date(2021, 6, 1): 0, date(2023, 6, 1): -1000})
    assert float(ds.red.isel(time=0).mean()) == pytest.approx(0.15)
    assert float(ds.red.isel(time=1).mean()) == pytest.approx(0.05)


def test_clear_fraction_and_select():
    ds = _fake_ds()
    assert list(s2.clear_fraction(ds).values) == [0.75, 1.0]
    kept = s2.select_clear(ds, min_clear=0.8)
    assert kept.sizes["time"] == 1


def test_offset_from_item_id():
    class Item:
        id = "S2B_MSIL2A_20240908T090559_N0511_R050_T35TMK_20240908T120000"
        properties, assets = {}, {}
    assert s2.offset_for_item(Item()) == -1000
    Item.id = Item.id.replace("N0511", "N0213")
    assert s2.offset_for_item(Item()) == 0


def test_pipeline_survives_unbuilt_modules():
    results = pipeline.run(make_parcel(box(21.22, 45.75, 21.23, 45.755)))
    assert {r.risk for r in results} == {"flood_history", "flood_susceptibility",
                                         "ground_stability", "land_use"}
    assert all(r.level == "Unknown" for r in results)
