"""Parcel geometry: the one input every module shares.

Conventions
- Geometries are stored in WGS84 (EPSG:4326) as (lon, lat), i.e. (x, y).
- All measuring (buffers, areas, pixel grids) happens in the parcel's UTM zone,
  chosen from the parcel itself. Romania spans zone 34 (west of 24°E, e.g.
  Timișoara) and zone 35 (east of 24°E, e.g. Galați). Never hard-code the zone.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from pyproj import Transformer
import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

WGS84 = 4326


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG code of the UTM zone containing (lon, lat). 326xx north, 327xx south."""
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def _reproject(geom: BaseGeometry, src: int, dst: int) -> BaseGeometry:
    # always_xy=True keeps (lon, lat) order and avoids the swapped-axis bug.
    t = Transformer.from_crs(src, dst, always_xy=True)
    return shapely.transform(geom, lambda x, y: t.transform(x, y), interleaved=False)


@dataclass(frozen=True)
class Parcel:
    geom_wgs84: BaseGeometry   # the client's parcel, (lon, lat)
    epsg: int                  # UTM zone used for all metric work
    geom_utm: BaseGeometry     # the parcel in UTM metres
    buffer_m: float            # how far around the parcel we look
    area_utm: BaseGeometry     # parcel + buffer, in UTM metres

    @property
    def area_wgs84(self) -> BaseGeometry:
        """Parcel + buffer back in WGS84, for STAC searches."""
        return _reproject(self.area_utm, self.epsg, WGS84)

    @property
    def bbox_wgs84(self) -> tuple[float, float, float, float]:
        """(west, south, east, north) of parcel + buffer, the STAC bbox order."""
        return self.area_wgs84.bounds

    @property
    def parcel_area_ha(self) -> float:
        return self.geom_utm.area / 10_000


def make_parcel(geom_wgs84: BaseGeometry, buffer_m: float = 500) -> Parcel:
    """Build a Parcel from a WGS84 polygon (e.g. drawn by the user or from cadastre)."""
    if geom_wgs84.is_empty or not geom_wgs84.is_valid:
        raise ValueError("Parcel geometry is empty or invalid")
    c = geom_wgs84.centroid          # c.x is lon, c.y is lat
    epsg = utm_epsg(c.x, c.y)
    geom_utm = _reproject(geom_wgs84, WGS84, epsg)
    return Parcel(geom_wgs84, epsg, geom_utm, buffer_m, geom_utm.buffer(buffer_m))


def parcel_from_geojson(geojson: str | dict, buffer_m: float = 500) -> Parcel:
    """Accepts a GeoJSON Geometry, Feature, or FeatureCollection with one feature."""
    g = json.loads(geojson) if isinstance(geojson, str) else geojson
    if g.get("type") == "FeatureCollection":
        g = g["features"][0]
    if g.get("type") == "Feature":
        g = g["geometry"]
    return make_parcel(shape(g), buffer_m)


# TODO (later): parcel_from_address(address) via geocoding, and
# parcel_from_cadastre(number) via ANCPI/eTerra, once we know what access we have.
