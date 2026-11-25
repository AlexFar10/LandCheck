"""Land-use module: summer NDVI per year, never a class (PRD Section 8.1)."""

from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")

from rasterio.transform import from_origin  # noqa: E402
from shapely.geometry import box  # noqa: E402

from landcheck.core import make_parcel  # noqa: E402
from landcheck.core.parcel import _reproject  # noqa: E402
from landcheck.modules import landuse  # noqa: E402

REAL = landuse.DEFAULT_RASTER
X0, Y0 = 560000.0, 5050000.0  # EPSG:32635 metres, near Pechea


def _raster(tmp_path: Path, values: dict[int, float]) -> Path:
    """10 x 10 pixels of 20 m; one band per year holding a constant (NaN allowed)."""
    path = tmp_path / "ndvi.tif"
    with rasterio.open(path, "w", driver="GTiff", height=10, width=10, count=len(values),
                       dtype="float32", crs="EPSG:32635", transform=from_origin(X0, Y0, 20, 20)) as ds:
        for i, (year, v) in enumerate(values.items(), start=1):
            ds.write(np.full((10, 10), v, dtype="float32"), i)
            ds.set_band_description(i, f"NDVI_{year}")
    landuse._years.cache_clear()
    return path


def _parcel(x: float, y: float, size: float = 60.0):
    utm = box(X0 + x, Y0 - y - size, X0 + x + size, Y0 - y)
    return make_parcel(_reproject(utm, 32635, 4326))


def test_reports_range_and_never_classifies(tmp_path):
    path = _raster(tmp_path, {2018: 0.5, 2019: 0.3, 2020: float("nan")})
    r = landuse.land_use(_parcel(40, 40), path)
    assert r.level == "Unknown" and r.unit == "median summer NDVI"
    assert r.details["summer_ndvi_by_year"] == {2018: 0.5, 2019: 0.3, 2020: None}
    assert "0.30 to 0.50" in r.summary and "does not show how the land was used" in r.summary


def test_sparse_vegetation_is_noted(tmp_path):
    r = landuse.land_use(_parcel(40, 40), _raster(tmp_path, {2018: 0.1, 2019: 0.05}))
    assert "sparse" in r.summary


def test_parcel_smaller_than_a_pixel_still_gets_a_value(tmp_path):
    r = landuse.land_use(_parcel(45, 45, size=5.0), _raster(tmp_path, {2018: 0.4}))
    assert r.value == 0.4 and r.details["pixels_used"] >= 1


def test_parcel_outside_raster_is_no_coverage(tmp_path):
    path = _raster(tmp_path, {2018: 0.4})
    r = landuse.land_use(make_parcel(box(21.22, 45.75, 21.23, 45.755)), path)
    assert r.summary.startswith("No coverage")


def test_parcel_partly_outside_says_so(tmp_path):
    r = landuse.land_use(_parcel(170, 40), _raster(tmp_path, {2018: 0.4}))  # 30 of 60 m inside
    assert r.details["parcel_inside_raster_pct"] == 50.0 and "50.0%" in r.summary


def test_missing_raster_is_no_coverage(tmp_path):
    assert landuse.land_use(_parcel(40, 40), tmp_path / "nope.tif").summary.startswith("No coverage")


@pytest.mark.skipif(not REAL.is_file(), reason="NDVI raster is not in git")
def test_real_raster_gives_eight_years():
    landuse._years.cache_clear()
    r = landuse.land_use(make_parcel(box(27.84, 45.62, 27.845, 45.625)), REAL)
    assert r.level == "Unknown" and len(r.details["summer_ndvi_by_year"]) == 8
