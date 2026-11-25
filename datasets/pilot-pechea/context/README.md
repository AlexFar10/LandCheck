# Context data for flood results (Pechea pilot)

Small rasters and a table used by `landcheck/modules/flood_context.py`. They add facts next to a
flood result and never change the level.

| File | What | Source | Notes |
|---|---|---|---|
| `ploaie_grid_pechea_sep2024.csv` | Daily rainfall (mm), 0.01 degree grid, September 2024 | ANM daily precipitation grid | Downloaded with the script in `docs/GHID_DESCARCARE_DATE_PECHEA.md` |
| `pechea_dem_relief.tif` | Elevation (m), 30 m, EPSG:32635 | Copernicus DEM GLO-30 | |
| `pechea_jrc_occurrence_v1_5_eocube.tif` | How often water was seen, 0-100 %, 255 = no data, 30 m, EPSG:32635 | JRC Global Surface Water v1.5 (via EOCube) | |
