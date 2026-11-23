# Implementation research dossier for a ROSPIN satellite-data masterclass project

## Project decision and candidate evaluation

The strongest five-week project is a Romanian surface-water and vegetation-stress monitoring application centered on the Lower Olt River reservoir cascade, with Sentinel-2 Level-2A as the primary high-resolution source and NASA Harmonized Landsat Sentinel-2 (HLS) as the preferred time-series source. The product should be framed as an Earth-observation monitoring and anomaly-screening tool, not as a system that diagnoses meteorological drought, predicts agricultural yield, or measures water quality.

This recommendation is unusually well aligned with the supplied ROSPIN curriculum. The ROSPIN Satellite Data Access Tools lesson already defines an end-to-end case study on "Reservoir & Drought Monitoring" across the Lower Olt River cascade, naming Lake Ipotești, Drăgănești, and Frunzaru and proposing Sentinel-2 processing. fileciteturn1file0 fileciteturn1file2 The same material explicitly contrasts downloading many full scenes with moving computation close to the data. fileciteturn0file3 The software-engineering lesson similarly teaches STAC, COG, Zarr and cloud-native access patterns rather than monolithic scene downloads. fileciteturn0file0

The project should improve on the lecture demonstration rather than simply reproduce it. The lecture example uses a simple `B3 > B8` water mask. fileciteturn1file0 For a student product, that is a useful baseline, but the implementation should add proper cloud and shadow masking, explicit nodata handling, season-matched anomalies, area uncertainty, a defensible water index, and a separate vegetation-moisture indicator for surrounding land. Sentinel-2 Level-2A supplies Bottom-of-Atmosphere surface reflectance plus a Scene Classification Layer, while HLS provides harmonized 30 m Landsat/Sentinel surface reflectance designed for common-grid time-series analysis. citeturn828441search1turn360731view3

Three candidate concepts were evaluated against the masterclass research principles. The ROSPIN research-methodology lesson explicitly recommends choosing questions that can be completed in five weeks, checking value, observability and novelty before committing, and warns against convenience sampling and weak validation. fileciteturn1file3 fileciteturn1file4

| Candidate | User value | Open data and reference data | Scientific tractability | Compute / engineering burden | Novelty for masterclass | Five-week feasibility | Decision |
|---|---|---|---|---|---|---|---|
| Lower Olt surface-water and vegetation-stress monitor | High for reservoir monitoring, educators, environmental analysts and local authorities; gives interpretable spatial/time-series outputs | Excellent: Sentinel-2, HLS, Landsat, ERA5-Land, CLMS; Romanian hydrological information exists, although historical station-level data access is not fully machine-friendly | Strong if claims are limited to observed surface-water extent and spectral vegetation/moisture anomalies | Low to moderate; can process a small AOI and selected bands only | Good if built as an auditable web product with HLS comparison, anomalies and provenance rather than another notebook | Very high | Recommended MVP |
| Galați September 2024 flood mapping | High emergency-management relevance | Excellent event reference: CEMS activation EMSR758; Sentinel-1 GRD available | Strong: radar flood delineation has a direct event/reference comparison | Moderate; SAR preprocessing and threshold sensitivity add complexity | Good research question, but close to the explicit ROSPIN methodology example | High | Best fallback / validation side-study |
| Urban heat and land-cover change, e.g. Bucharest | High public-interest value | Landsat Collection 2 Surface Temperature and CLMS land cover are available | Valid for surface temperature, but easy to overstate as human heat exposure; cloud-free temporal sampling and emissivity issues need care | Moderate | Common EO project topic | Medium-high | Not preferred |

The Galați option is particularly defensible scientifically because the supplied ROSPIN methodology lesson gives almost exactly the research question: compare a radar flood method against a simple baseline using the September 2024 Galați event and Copernicus EMS reference data. fileciteturn1file3 Copernicus EMS confirms that activation EMSR758 covered the 14 September 2024 floods in Galați and Vaslui and that Rapid Mapping was requested for flood extent and damage assessment. citeturn360731view5 That makes it excellent for a methodological comparison, but it is less differentiated from the course material than a polished Olt monitoring product.

The urban-heat option is technically viable because Landsat Collection 2 provides Level-2 Surface Temperature, with the official conversion `ST = DN × 0.00341802 + 149.0` K. citeturn427615search7 It should nevertheless be described as land-surface temperature, not human thermal exposure or air temperature, which makes its product story somewhat harder to communicate correctly.

The recommended product is therefore:

"Lower Olt EO Monitor: a web application that lets a user inspect seasonal surface-water extent and surrounding vegetation-moisture anomalies for selected Lower Olt reservoirs using public satellite observations, with downloadable maps, time series, quality flags and full data provenance."

The target personas are an environmental analyst who wants a rapid screening view before deeper hydrological work; a local or basin-level water-management user who wants to inspect how observed reservoir surface extent differs from normal seasonal conditions; a researcher or student who wants a reproducible EO time series; and a public-facing educator who wants a transparent map rather than a black-box "drought score."

The core user workflows are: choose a predefined Lower Olt reservoir or draw an AOI; choose a date or date range; inspect a cloud-filtered surface-water map; compare current water extent with a season-matched historical baseline; inspect vegetation-moisture and NDVI time series around, but not inside, the reservoir; inspect acquisition and quality metadata; and export CSV, GeoJSON and a georeferenced raster.

A good live demo is "May versus August for one reservoir, then compare August with the same calendar window in prior years." That reproduces the pedagogical logic of the ROSPIN Olt example while avoiding the false inference that a spring-to-summer reduction automatically proves drought. The measurable product outcomes for the MVP should be operational rather than invented accuracy numbers: a user can generate a result for the predefined AOIs; every result records source item IDs, acquisition dates and processing parameters; invalid/cloudy observations are explicitly flagged; raster and tabular exports are reproducible; and the same processing request gives the same result against pinned source items and code revision.

The primary research hypothesis should be:

"For predefined Lower Olt reservoir AOIs, a cloud-masked Sentinel-2 or HLS index-based water-extraction workflow with a season-matched historical reference will provide more stable estimates of surface-water extent than the lecture's single-date `Green > NIR` rule when evaluated against independently inspected reference samples and, where obtainable, official hydrological observations."

This is deliberately testable without asserting that either method measures hydrological drought. The simple reproducible baseline is exactly the lecture rule: classify water where Sentinel-2 green reflectance exceeds NIR reflectance after masking invalid pixels. The improved method can use McFeeters NDWI plus conservative thresholding and temporal compositing. The research metric should be determined only after an independent reference sample is created; appropriate map metrics include intersection-over-union, precision/recall or area error, but no target score should be invented in advance.

## Product definition and scientific framing

The MVP should distinguish three things that are often incorrectly conflated: surface-water detection, vegetation water/moisture response, and meteorological/hydrological drought.

For open-water delineation, use the McFeeters form:

\[
NDWI_{water}=\frac{\rho_{green}-\rho_{NIR}}
{\rho_{green}+\rho_{NIR}}
\]

McFeeters' index was designed to enhance open water using green and near-infrared reflectance. The published equation is Green minus NIR divided by Green plus NIR. citeturn427615search4 For Sentinel-2, the practical pairing is B03 and B08.

A different index was also named NDWI by Gao:

\[
NDWI_{Gao}=\frac{\rho_{NIR}-\rho_{SWIR}}
{\rho_{NIR}+\rho_{SWIR}}
\]

Gao's 1996 index was introduced for vegetation liquid-water sensitivity, originally using approximately 0.86 µm and 1.24 µm channels. citeturn427615search0turn427615search10 The name collision is important. The application UI and API should never expose a generic field called only `ndwi`; use `ndwi_water_mcfeeters` and `ndwi_vegetation_gao` if both are implemented.

For Sentinel-2 vegetation moisture, the more practical product index is usually NDMI using NIR and SWIR:

\[
NDMI=\frac{\rho_{NIR}-\rho_{SWIR1}}
{\rho_{NIR}+\rho_{SWIR1}}
\]

USGS documents the same NIR/SWIR form for NDMI and describes it as an indicator of vegetation water content. citeturn427615search1 For Sentinel-2, use B08 or B8A consistently with B11 depending on the harmonization strategy; B11 is native 20 m, so the analysis grid must be explicit. Do not silently treat a resampled 20 m band as genuine 10 m information.

NDVI can be retained as a secondary vegetation-state indicator:

\[
NDVI=\frac{\rho_{NIR}-\rho_{red}}
{\rho_{NIR}+\rho_{red}}
\]

The application should report these as spectral observations or anomalies. It must not say that a low NDMI alone establishes agricultural drought, crop damage or yield loss.

The baseline/anomaly design should compare like with like. For date \(t\), define a season-matched historical baseline from the same approximate day-of-year window, such as ±15 days over earlier years:

\[
A_t = X_t-\operatorname{median}(X_{y,\;DOY(t)\pm w})
\]

and, where enough valid historical observations exist,

\[
Z_t=
\frac{X_t-\operatorname{median}(X_{hist})}
{1.4826\,MAD(X_{hist})}
\]

A robust median/MAD anomaly is preferable to an unqualified z-score for short or skewed EO series. This is a recommended design choice, not an assertion from the input course.

For water extent, the application should calculate:

\[
Area_{water}=\sum_{i \in valid} I_i\,A_i
\]

where \(I_i\) is 1 for classified-water pixels and \(A_i\) is the pixel area in an appropriate projected CRS. Do not compute hectares by multiplying degrees in EPSG:4326. Reproject or calculate area on a suitable projected grid.

Clouds, cloud shadows, snow, saturated pixels and nodata must be removed before any index or composite. Sentinel-2 L2A exposes SCL classes including nodata, saturated/defective, cloud shadow, medium/high cloud probability, cirrus and snow/ice; the CDSE documentation also exposes `dataMask`. citeturn828441search0 A conservative optical mask should reject at minimum SCL 0, 1, 3, 8, 9, 10 and 11; treating SCL 7 as invalid is also defensible for the MVP and is consistent with one CDSE mosaic example. citeturn828441search2 Optionally dilate cloud and shadow masks one or two pixels to reduce contaminated edges, but record the dilation radius in provenance.

Sentinel-2 reflectance scaling must be explicit. In the Sentinel Hub representation of Sentinel-2 L2A, `DN = 10000 × reflectance`; an implementation reading raw integer assets must inspect source metadata rather than blindly assume floating reflectance. citeturn828441search0 Landsat Collection 2 surface reflectance uses `reflectance = DN × 0.0000275 - 0.2`. citeturn813360search6 HLS should be processed according to its product metadata/user guide instead of applying Sentinel-2 or Landsat scaling rules interchangeably.

The app should report two types of uncertainty. "Observation quality" comes from usable-pixel fraction, cloud/shadow fraction, number of valid acquisitions contributing to a composite, and source-mask status. "Method uncertainty" comes from threshold sensitivity and disagreement between baseline and improved classification. A useful MVP display is a sensitivity band generated from a small fixed threshold range established before validation, rather than displaying a single water-area number with false precision.

Any machine-learning stretch feature must avoid pixel-random train/test splits. The supplied ROSPIN methodology explicitly warns that the reference unit constrains valid inference and recommends locking away test data rather than repeatedly inspecting it. fileciteturn1file4 If a classifier is later trained, split by whole reservoir and/or whole year so that nearby pixels from the same acquisition cannot leak into both train and test.

## Verified data catalog

All web sources in this section were accessed on 2026-11-22. Where a service's current access conditions could change, the implementation should perform a week-one smoke test and save the returned service metadata.

| Dataset / product | Producer and Romanian coverage | Temporal / spatial characteristics | Relevant bands and QA | Access / API | Authentication / quotas | License / attribution | Data-volume strategy | MVP role and validation value |
|---|---|---|---|---|---|---|---|---|
| Sentinel-2 Level-2A Collection 1 | Copernicus/ESA; Europe including all Romania | Surface reflectance; 10 m, 20 m and 60 m source bands depending on wavelength. L2A includes surface reflectance and SCL. citeturn828441search1turn766839search6 | B02/B03/B04/B08 at 10 m; red-edge/SWIR bands include 20 m products; SCL is 20 m native in L2A. citeturn828441search0turn828441search1 | CDSE STAC: `https://stac.dataspace.copernicus.eu/v1/`; Sentinel Hub Process API; CDSE S3 at `https://eodata.dataspace.copernicus.eu/`. STAC currently lists Sentinel-2 L2A. citeturn360731view0turn813360search1 | CDSE account required for authenticated S3/processing use. General-user quotas currently include 2,000 S3 requests/min, 12 TB rolling transfer for immediately available data, 10,000 Sentinel Hub requests/month and 10,000 PU/month; quotas are time-sensitive. citeturn360731view2 | Sentinel data are free, full and open under the Sentinel legal notice. CDSE terms explicitly state free, full and open Sentinel access. `https://dataspace.copernicus.eu/terms-and-conditions` citeturn766839search5 | Never download nationwide archives. Query by AOI/date, request selected bands, or cache cropped outputs. | Primary 10–20 m source for reservoir boundary mapping and visual demo. |
| Sentinel-1 GRD | Copernicus/ESA; Romania covered by Sentinel acquisition plan and archive | C-band SAR GRD; useful independent of optical cloud cover | VV/VH depending on acquisition; processing may include calibration, thermal-noise removal, orthorectification and optional terrain correction through Sentinel Hub. citeturn813360search4 | Same CDSE STAC endpoint; currently includes Sentinel-1 GRD. Sentinel Hub type `sentinel-1-grd`. citeturn360731view0turn813360search4 | CDSE account / current quotas as above for processing and direct data access | Sentinel open-data terms as above. citeturn766839search5 | Fetch only event windows and AOI subsets. SAR processing is heavier than the optical MVP. | Stretch goal or Galați fallback. Valuable for cloudy flood events and cross-sensor comparison. |
| HLS L30 v2.0 | NASA LP DAAC, derived from Landsat 8/9; global land including Romania | 30 m common MGRS grid; coverage from first Landsat-8 acquisitions in 2013 onward. HLS combines harmonized Landsat/Sentinel inputs into common-grid time series. citeturn360731view3 | L30 provides Landsat-like surface-reflectance bands plus Fmask and angle bands. HLS cloud/shadow QA is based on Fmask. citeturn360731view3turn726653search2 | NASA Earthdata Search and Earthdata Cloud. HLS products are distributed as per-band COGs. `https://hls.gsfc.nasa.gov/data-access-and-tools/` citeturn813360search5 | Free Earthdata Login for direct download/access workflows. citeturn726653search11 | NASA Earth-science data are distributed under NASA's open-data policy; retain dataset citation and DOI. HLS L30 DOI `10.5067/HLS/HLSL30.002`. citeturn766839search4turn726653search6 | Excellent cloud-native option because individual bands are COGs; read AOI windows only. | Preferred historical time-series source; reduces Landsat/Sentinel inter-sensor harmonization work. |
| HLS S30 v2.0 | NASA LP DAAC, derived from Sentinel-2 A/B/C inputs; global land including Romania | 30 m common MGRS grid, Sentinel archive from 2015 onward. Current HLS user guide describes Sentinel-2 A/B/C inputs and common 30 m gridding. citeturn360731view3 | 13 reflectance bands plus Fmask and angle bands in S30; Fmask contains cloud, adjacent cloud/shadow, cloud shadow, snow/ice and water flags. citeturn726653search0turn726653search1 | Earthdata / LP DAAC; COG-per-band distribution. `https://hls.gsfc.nasa.gov/data-access-and-tools/` citeturn813360search5 | Earthdata Login for direct data workflows. | NASA open-data policy; cite HLS S30 dataset and LP DAAC. | AOI window reads from COG assets. | Combine with L30 for dense, harmonized historical observations. |
| Landsat 8/9 Collection 2 Level-2 Surface Reflectance | USGS/NASA; worldwide including Romania | 30 m surface reflectance; Landsat 8/9 scene repeat is slower than Sentinel but archive is long-lived. | SR bands plus `QA_PIXEL` and `QA_RADSAT`. Collection 2 SR scale factor is 0.0000275 with -0.2 offset. citeturn813360search6turn813360search7 | EarthExplorer; LandsatLook STAC at `https://landsatlook.usgs.gov/stac-server`; Collection `landsat-c2l2-sr`; AWS direct cloud access also available. citeturn198887search0turn198887search2 | EarthExplorer account may be required for traditional workflows; direct AWS access requires an AWS account and vendor costs may apply although Landsat itself remains no-cost. citeturn198887search5 | USGS Landsat data remain no-cost under the open-data policy. citeturn198887search6 | Prefer STAC/COG window access or HLS instead of scene downloads. | Cross-check / fallback source. Avoid duplicating HLS processing unless needed. |
| Landsat Collection 2 Level-2 Surface Temperature | USGS/NASA; worldwide | Level-2 surface-temperature product; delivered on Landsat product grid. Official conversion is `DN × 0.00341802 + 149 K`. citeturn427615search7 | ST band plus QA; thermal source characteristics differ from optical bands | Same USGS access routes | Same as Landsat | Same Landsat policy | Fetch only if urban-heat option is pursued | Not part of recommended MVP; basis of candidate three. |
| CLMS Water and Wetness Status 2018 | Copernicus Land Monitoring Service; pan-European including Romania | 10 m and 100 m status product describing water/wet-surface occurrence over 2012–2018; Europe-wide 10 m package is listed as 2 GB. citeturn828441search4 | Categorical water/wetness raster | CLMS portal/download API. `https://land.copernicus.eu/en/products/high-resolution-layer-water-and-wetness/water-and-wetness-status-2018` | Portal currently requires login for download. citeturn828441search7 | Full, open and free; derivatives must acknowledge CLMS and indicate modifications. `https://land.copernicus.eu/en/data-policy` citeturn639528search0 | Download Romanian/AOI tile only | Historical contextual layer, not contemporary ground truth. Useful to mask permanent water or inspect plausibility. |
| CORINE Land Cover 2018 | CLMS / EEA; Europe including Romania | 100 m raster plus vector delivery; temporal coverage 2017–2018. citeturn828441search3turn828441search8 | Categorical land cover | CLMS download/API | CLMS login for current download portal | CLMS attribution terms as above. citeturn639528search0 | Small enough to cache Romania/AOI | Mask or stratify vegetation/urban/agricultural surroundings; not a current land-cover truth layer. |
| ERA5-Land | Copernicus Climate Change Service / ECMWF | 1950-present, hourly; 0.1° output grid with native model resolution about 9 km. citeturn828441search5 | Precipitation, soil moisture, temperature and other land variables | CDS API / portal. `https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land` | CDS account; terms must be accepted before API requests. citeturn828441search6 | Dataset page currently specifies CC-BY. citeturn828441search5 | Request only Olt bounding box, variables and dates needed | Contextual meteorology. Suitable to test whether observed EO anomalies coincide with dry conditions, but too coarse to "validate" 10–30 m water boundaries. |
| INHGA hydrological bulletins | Romanian National Institute of Hydrology and Water Management | National and basin-level current/historical bulletin products; site publishes daily/informative/monthly hydrological bulletins and station trends. citeturn360731view4 | River-flow/state information, varying by publication | `https://www.hidro.ro/`; no verified public machine API found during this research | Public website; programmatic terms/quotas not identified | Reuse/licensing terms for machine ingestion were not verified; treat as reference-only until confirmed | Manual or separately approved ingestion | Potential independent hydrological context. Access is the principal uncertainty. |
| ABA Olt hydrological records | Administrația Bazinală de Apă Olt / Apele Române | Basin-specific. Public-information catalogue states that daily flows and levels at main hydrometric stations exist, and that inflows to principal lakes for up to 30 days can be made public on request. citeturn372954search0 | Station flow/level records | `https://olt.rowater.ro/`; current site points to hydrological-status resources. citeturn372954search1 | No stable public API verified | Access and reuse terms for automated use are uncertain | Do not make MVP dependent on automated access | Best candidate for human-obtained independent context; explicitly mark "pending access verification." |
| Copernicus EMS EMSR758 | Copernicus Emergency Management Service | Galați and Vaslui, September 2024 | Rapid Mapping flood extent/damage outputs | `https://mapping.emergency.copernicus.eu/news/flood-in-galati-and-vaslui-counties-romania/` | Public product viewing/download except sensitive activations. citeturn954690search4 | Copernicus EMS public product; retain required Copernicus attribution | Only small event reference layers | High-quality reference for the alternative Galați research experiment, not the Olt MVP. |

The direct CDSE STAC endpoint currently supports both Sentinel-1 GRD and Sentinel-2 Level-2A collections, and the CDSE documentation explicitly demonstrates date, spatial and cloud-cover filtering for Sentinel-2 L2A. citeturn360731view0 The endpoint changed after a legacy STAC endpoint was deprecated in November 2025, so old tutorials using `catalogue.dataspace.copernicus.eu/stac` should not be copied blindly. citeturn360731view0

HLS is especially attractive for this project because the April 2026 HLS v2.0 user guide states that L30 and S30 are gridded to the same MGRS tiles at 30 m and that the processing includes atmospheric correction, cloud/shadow masking, co-registration, view-angle normalization and spectral-bandpass adjustment. citeturn360731view3turn455294view0 This directly reduces one of the biggest scientific risks in naïvely concatenating raw Landsat and Sentinel-2 time series.

The app should not depend on Romanian station data for completion. The evidence shows that relevant Olt basin daily flow/level records exist institutionally, but a stable public data API and explicit machine-reuse terms were not verified. citeturn372954search0turn372954search1 Treat those records as an optional independent validation/context source to be requested early in week one.

## Processing and validation workflow

The first reproducible AOIs should be the three Lower Olt reservoirs named in the ROSPIN material: Ipotești, Drăgănești and Frunzaru. fileciteturn1file0 The team should store reviewed GeoJSON polygons in the repository rather than relying on ambiguous place-name geocoding during processing. Their provenance should record who digitized or sourced each boundary, source imagery/date, CRS and a checksum.

The initial retrieval plan should not claim that data have already been downloaded. It should be implemented as a reproducible script:

```text
1. Load a versioned AOI GeoJSON.
2. Query Sentinel-2 L2A from the CDSE STAC endpoint for:
   - AOI intersection
   - candidate summer analysis window
   - candidate spring comparison window
   - several prior years for the same seasonal windows
3. Filter only on broad scene-level cloud metadata initially.
4. Fetch required assets/subsets, then apply pixel-level SCL masking.
5. In parallel, query HLS L30/S30 for the same AOI and seasonal windows.
6. Store source STAC Items/CMR metadata unchanged beside derived outputs.
7. Compute baseline and improved water classifications.
8. Generate per-date/per-composite water area and valid-pixel fraction.
9. Compute land-only NDVI/NDMI in a buffered reservoir-adjacent zone.
10. Build historical season-matched medians and anomalies.
11. Export a COG/GeoTIFF, CSV, GeoJSON summary and provenance JSON.
```

A sensible first experiment is a single reservoir and two short seasonal windows rather than all three reservoirs and all years. The exact dates should be selected only after the catalogue query shows valid acquisitions. The application can begin with May and August windows because that is the comparison framed in the supplied ROSPIN Olt exercise, but it should not hard-code an unsupported label such as "severe drought" into the API or UI. fileciteturn1file0

The optical processing chain should be:

```text
AOI
-> STAC/CMR search
-> source-item manifest
-> asset/window read
-> scale to physical reflectance where required
-> nodata + SCL/Fmask rejection
-> common analysis CRS/grid
-> optional cloud-mask dilation
-> index computation
-> per-date classification
-> within-window robust composite
-> zonal area/statistics
-> same-season historical reference
-> anomaly calculation
-> validation diagnostics
-> COG + tabular outputs
-> tile service
```

For Sentinel-2, use a 10 m grid only for quantities derived exclusively from 10 m bands, such as McFeeters water NDWI from B03/B08. For NDMI involving B11, either calculate at 20 m or explicitly resample all inputs to a chosen target grid. The preferred scientific choice is 20 m for B08/B11 NDMI rather than implying that resampling B11 to 10 m creates extra spatial information.

For HLS, keep the native 30 m common MGRS grid. Do not compare Sentinel-2 10 m area pixel-for-pixel with HLS 30 m classification and interpret the difference as sensor error. Compare aggregated area/statistics or explicitly resample to a common analysis grid.

For compositing, a median of valid reflectance or index observations within a narrow date window is defensible for a five-week MVP. Store `n_valid_observations` per pixel if feasible, and always expose an AOI-level `valid_fraction`. If valid coverage is below a team-defined threshold, return a low-quality flag rather than silently generating a polished-looking map.

The primary water baseline is:

```python
water_baseline = green_reflectance > nir_reflectance
```

The improved method is:

```python
ndwi_water = (green - nir) / (green + nir)
water_improved = (ndwi_water > threshold) & valid_mask
```

The threshold must not be tuned on the final test reference. Select it from literature/default exploration or an explicitly separated calibration subset, then freeze it before evaluating the held-out AOI/date.

Permanent-water context from CLMS Water and Wetness can help separate expected reservoir surface from newly detected flood/wetness patterns, but the 2018 product should not be called current ground truth. CLMS describes it as a 2012–2018 water/wetness occurrence product. citeturn828441search4

For independent reference labels, randomly sample points or small polygons within stratified zones such as likely water, shoreline and likely non-water, then have a human label them from a higher-confidence visual reference without seeing the method output. The sampling frame and keep/drop rules should be frozen before final evaluation, consistent with the ROSPIN methodology lesson. fileciteturn1file4 If official reservoir level or discharge observations become accessible, compare temporal direction and timing, not pixel-level segmentation accuracy.

For an ML stretch goal, the test split must be spatially and temporally independent. One reasonable scheme is train on two reservoirs and earlier years, tune on a different year, then test on the third reservoir or a fully held-out year. Pixel-random splitting is prohibited because neighboring pixels from the same acquisition share acquisition conditions and spatial autocorrelation.

Every derived artifact should carry at least:

```json
{
  "algorithm": "water_ndwi_mcfeeters_v1",
  "code_commit": "git-sha",
  "created_at": "UTC timestamp",
  "aoi_id": "olt_draganesti_v1",
  "source_provider": "CDSE",
  "source_collection": "Sentinel-2 L2A",
  "source_item_ids": [],
  "source_datetimes": [],
  "bands": ["B03", "B08", "SCL"],
  "reflectance_scaling": "...",
  "mask_policy": {
    "scl_excluded": [0, 1, 3, 7, 8, 9, 10, 11],
    "dilation_pixels": 1
  },
  "analysis_crs": "EPSG:...",
  "resolution_m": 10,
  "composite": "median",
  "threshold": 0.0,
  "valid_fraction": 0.0,
  "license_attribution": "...",
  "source_metadata_sha256": "..."
}
```

The `threshold` value above is only a schema example; it is not a recommended scientific threshold unless the team explicitly adopts and validates it.

## System architecture, frontend and API contract

The lowest-cost architecture is a modular monolith rather than microservices. That matches the five-week schedule and keeps geospatial debugging in one codebase. The frontend is React/TypeScript; the backend is Python/FastAPI; PostgreSQL/PostGIS stores AOIs, jobs and statistics; an S3-compatible object store stores COGs, source manifests and exports; and a worker performs the heavier raster processing. TiTiler or a small rio-tiler integration serves map tiles from the generated COGs. TiTiler's documented model is dynamic tile generation over COG/STAC sources, avoiding the need to pre-render every zoom level. citeturn844717search1turn844717search2

Recommended backend stack:

```text
Python 3.x
FastAPI
Pydantic
SQLAlchemy or SQLModel + Alembic
PostgreSQL + PostGIS
pystac-client
rasterio
rioxarray
xarray
numpy
pandas
geopandas
shapely
pyproj
rio-tiler or TiTiler
httpx
redis
RQ / Dramatiq / Celery for durable jobs
pytest
```

`pystac-client` is appropriate because it is explicitly designed for STAC API search endpoints. citeturn844717search7 FastAPI's built-in `BackgroundTasks` is useful for short post-response work, but raster jobs should use a durable worker queue because the web process may restart and long-running work should not depend on a single HTTP process. FastAPI itself documents in-process background-task support. citeturn844717search0

Dask should remain optional. For three small AOIs, narrow date windows and windowed COG reads, NumPy/xarray/rasterio are simpler and easier to debug. Add Dask only after profiling shows a real memory or parallelism problem.

Recommended frontend stack:

```text
React + TypeScript
Vite
MapLibre GL JS
@mapbox/mapbox-gl-draw-compatible drawing library or Terra Draw
TanStack Query
ECharts, Recharts or Vega-Lite wrapper
Zod for client-side validation
React Router
```

MapLibre avoids binding the MVP to a proprietary map-rendering SDK. The frontend should render server-provided raster tiles plus GeoJSON overlays; it should never receive CDSE client secrets.

The practical data-platform tradeoff is:

| Approach | Strengths | Weaknesses | Recommended use |
|---|---|---|---|
| CDSE STAC + Sentinel Hub/S3 | Official Copernicus access; strong Sentinel coverage; STAC is now an official CDSE catalogue; student-friendly free quota | Authentication and current quota rules need handling; raw product structures can be more awkward than HLS | Primary source for Sentinel-2 10 m final maps |
| NASA HLS COGs | Harmonized Landsat/Sentinel time series, common 30 m grid, per-band COG distribution | 30 m instead of Sentinel-2 10 m; Earthdata authentication/access flow | Preferred time-series and cross-sensor source |
| Google Earth Engine | Very fast prototyping and mature catalog; excellent for initial scientific exploration | Platform-specific APIs and compute model create vendor lock-in; production app would depend on GEE project access and quota | Prototype / cross-check, not core production dependency |
| Direct Landsat STAC/AWS | Official USGS catalog and COG access | AWS direct data path can incur vendor processing/storage/egress costs; redundant if HLS is already used | Fallback / scientific cross-check |

As of 2026, Google Earth Engine noncommercial projects use recurring EECU quotas. The Community tier is documented as 150 EECU-hours/month and is explicitly described as suitable for undergraduates; the Contributor tier is 1,000 EECU-hours/month and requires a billing account even though noncommercial Earth Engine usage itself is not charged. citeturn766839search0 This makes GEE attractive for research prototyping, but a public web application coupled directly to a student GEE project inherits platform access and quota constraints. Earth Engine project registration and noncommercial verification are also required. citeturn766839search2

The production MVP should therefore use direct official catalog/data access and cache derived outputs. GEE can remain a notebook validation path that checks whether the team's direct pipeline reproduces the same broad temporal patterns.

A local Docker Compose topology can be:

```text
frontend
api
worker
postgres-postgis
redis
minio
```

For a modest deployment, combine `api` and the worker onto one small VM/container host if necessary. Store only cropped or derived AOI artifacts, not a local mirror of Sentinel archives. Set object lifecycle rules on temporary rasters. A student budget cap should be enforced through provider billing alerts and by rejecting oversized jobs before processing. No numeric monthly cloud budget should be hard-coded into the PRD until the team selects its hosting provider and credits.

Security constraints should include server-side secrets only; separate development and production credentials; OAuth/service credentials in environment secrets, never the React bundle; AOI coordinate/vertex limits; request body limits; timeout and retry budgets; SSRF protection if any backend route accepts asset URLs; CORS restricted to known frontend origins; parameterized SQL; validation of uploaded GeoJSON; and no arbitrary user-supplied GDAL path, file URL or evalscript execution.

The API contract can be:

```http
GET /api/v1/aois
GET /api/v1/aois/{aoi_id}

POST /api/v1/analyses
GET /api/v1/analyses/{analysis_id}
GET /api/v1/analyses/{analysis_id}/timeseries
GET /api/v1/analyses/{analysis_id}/layers
GET /api/v1/analyses/{analysis_id}/exports/{format}

GET /api/v1/tiles/{layer_id}/{z}/{x}/{y}.png

GET /api/v1/catalog/search
GET /api/v1/health
GET /api/v1/version
```

Example request:

```json
POST /api/v1/analyses

{
  "aoi_id": "olt_draganesti_v1",
  "date_range": {
    "start": "2024-08-01",
    "end": "2024-08-31"
  },
  "baseline": {
    "type": "seasonal_median",
    "years": [2019, 2020, 2021, 2022, 2023],
    "day_window": 15
  },
  "source": "sentinel-2-l2a",
  "products": [
    "water_extent",
    "ndwi_water_mcfeeters",
    "ndvi",
    "ndmi"
  ]
}
```

Example asynchronous response:

```json
{
  "analysis_id": "01J...",
  "status": "queued",
  "created_at": "2026-11-22T12:00:00Z",
  "links": {
    "self": "/api/v1/analyses/01J..."
  }
}
```

Job states should be:

```text
queued
catalog_search
fetching
processing
validating
publishing
succeeded
failed
cancelled
```

A completed response should include data-quality information rather than only the headline value:

```json
{
  "analysis_id": "01J...",
  "status": "succeeded",
  "summary": {
    "water_area_ha": 412.6,
    "baseline_water_area_ha": 455.2,
    "anomaly_ha": -42.6
  },
  "quality": {
    "valid_fraction": 0.91,
    "source_observation_count": 4,
    "flag": "good"
  },
  "provenance": {
    "source_items": ["..."],
    "algorithm": "water_ndwi_mcfeeters_v1",
    "code_commit": "..."
  }
}
```

Those numbers are illustrative API examples only and must never appear as demo results unless produced from real data.

Input limits for the MVP should be explicit: Romania-only geometry, maximum AOI area, maximum vertex count, maximum date span, maximum number of products and maximum historical baseline years. The exact numeric caps can be chosen after one week of profiling. Reject self-intersecting polygons, coordinates outside Romania, requests with no catalog results, unsupported CRS, date ranges in the future, impossible source/product combinations and jobs whose estimated work exceeds configured limits.

Recommended error model:

```json
{
  "error": {
    "code": "INSUFFICIENT_VALID_PIXELS",
    "message": "The selected period contains too little cloud-free coverage.",
    "details": {
      "valid_fraction": 0.18
    }
  }
}
```

Initial PostGIS tables:

```text
aoi
- id UUID PK
- slug TEXT UNIQUE
- name TEXT
- geom geometry(MultiPolygon, 4326)
- source TEXT
- version INTEGER
- created_at timestamptz

analysis
- id UUID PK
- aoi_id UUID FK
- status TEXT
- request JSONB
- algorithm_version TEXT
- git_commit TEXT
- created_at timestamptz
- started_at timestamptz
- finished_at timestamptz
- error JSONB

source_item
- id UUID PK
- analysis_id UUID FK
- provider TEXT
- collection TEXT
- item_id TEXT
- datetime timestamptz
- metadata JSONB
- metadata_sha256 TEXT

observation_stat
- id UUID PK
- analysis_id UUID FK
- observed_at timestamptz
- metric TEXT
- value DOUBLE PRECISION
- unit TEXT
- valid_fraction DOUBLE PRECISION
- quality_flag TEXT

artifact
- id UUID PK
- analysis_id UUID FK
- kind TEXT
- uri TEXT
- media_type TEXT
- checksum_sha256 TEXT
- metadata JSONB
```

Object storage:

```text
s3://rospin-eo/
  source-manifests/{analysis_id}/
  intermediate/{analysis_id}/
  rasters/{analysis_id}/
  exports/{analysis_id}/
  fixtures/
```

Repository structure:

```text
/apps
  /web
  /api
/packages
  /eo
    catalog/
    masking/
    indices/
    composites/
    zonal/
    provenance/
  /schemas
/workers
/infra
  docker/
  migrations/
/data
  aois/
  fixtures/
/notebooks
/tests
  unit/
  integration/
  scientific/
  e2e/
/docs
```

The web UI needs only five pages for the MVP: landing/project-methodology page; map/AOI selection page; analysis configuration panel; result dashboard with map and time-series chart; and provenance/export page. A separate "methodology" drawer should explain what each index means and, crucially, what it does not mean.

## Delivery plan, acceptance criteria, validation and risks

The backlog should be sequenced so that scientific correctness precedes visual polish.

Week one should finish the data-access spike and lock the science contract. The team creates the three reviewed AOI polygons, runs live catalogue queries against CDSE and HLS, verifies authentication, persists one real source manifest, implements reflectance scaling and masks against small fixtures, and freezes the baseline/improved-method definitions. Acceptance requires that one command can search at least one Olt AOI and return real source item metadata without manually editing code. No frontend map is required yet.

Week two should finish the reproducible analysis pipeline. Implement Sentinel-2 water masks, HLS ingestion, NDVI/NDMI, composites, zonal area, seasonal historical baseline and COG/CSV outputs. Acceptance requires deterministic outputs for test fixtures, unit tests for equations and QA bits, and a result JSON containing provenance and valid-pixel statistics.

Week three should finish backend jobs and map delivery. Implement PostGIS models, async worker lifecycle, object storage, tile serving and the analysis API. Acceptance requires a full API request to queue a job and eventually return a rendered layer plus time-series JSON; restarting the API must not lose a queued/running job record.

Week four should finish the React product and research evaluation. Implement AOI selector/drawing, date controls, map overlays, charts, quality warnings, methodology/provenance panel and downloads. Freeze the reference labels before final baseline-versus-improved evaluation. Acceptance requires that a new user can run the predefined demo without opening a notebook or terminal.

Week five should be stabilization and demonstration. Repeat the analysis from a clean checkout, measure API/job timing, fix attribution, produce the demo dataset manifest, run accessibility/security checks, and document negative or ambiguous findings. Acceptance requires a fresh `docker compose up` followed by the documented demo flow, plus a final evaluation report that includes both successes and failure cases.

MVP acceptance criteria should include:

- AOIs: user can select at least the predefined Lower Olt reservoirs; geometry is versioned and visible on the map.
- Search: backend finds public EO observations by AOI/date and records source IDs.
- Masking: clouds, shadows, nodata and invalid observations are excluded according to a documented policy.
- Water analysis: app computes baseline `Green > NIR` and improved McFeeters NDWI outputs independently.
- Vegetation context: app computes NDVI and NDMI on land surrounding the reservoir, not as a substitute for water extent.
- Temporal analysis: app provides same-season historical median and anomaly, with the baseline years shown to the user.
- Quality: every result includes valid-pixel fraction and observation count.
- Map: georeferenced result renders in the browser and aligns with the AOI.
- Export: CSV plus GeoTIFF/COG or GeoJSON export is downloadable.
- Provenance: source collection/item IDs, acquisition dates, algorithm version, mask rules and code revision are visible.
- Reproducibility: fixture tests pass and a clean environment can recreate the demo.
- Claims: UI never describes an EO index alone as proof of meteorological drought, crop yield, water quality or reservoir storage volume.

Definition of done for any scientific feature should mean code, test, documentation, provenance metadata, UI explanation and a known-limitations entry are all present. A feature that produces a number without explaining source, units, masking and uncertainty is not done.

Scientific validation should compare the lecture baseline against the improved method on a frozen independent label set. Report a confusion matrix and spatial-overlap metrics if the reference has pixel/polygon labels; report only area/timing agreement if the independent reference is hydrological. Do not transform coarse or indirect hydrological data into invented pixel labels.

If an ML extension is attempted, pre-register the split before model fitting. Split by reservoir/year, keep the test set inaccessible during tuning, and report negative results. The supplied ROSPIN methodology explicitly warns that easy/convenience samples produce misleading accuracy. fileciteturn1file4

Stretch features, in priority order, are Sentinel-1 water/flood cross-checking; ERA5-Land precipitation/soil-moisture context; automated ingestion of an official Romanian hydrological series if permissions and access are verified; threshold-sensitivity visualization; multi-reservoir comparison; user-uploaded AOIs; and only then a supervised classifier. A pretrained deep-learning model is not an MVP requirement.

Nonfunctional requirements should include p95 API metadata endpoints under a few seconds excluding analysis jobs; analysis jobs asynchronous; deterministic processing against pinned inputs; graceful degradation when an upstream provider is unavailable; retries with exponential backoff for rate-limited providers; no upstream credentials in browser code; no personally identifying data required for the core application; keyboard-accessible controls and readable chart alternatives; visible source attribution; generated artifacts checksummed; structured logs containing job ID but not secrets; health/readiness endpoints; and a small number of operational metrics such as queue depth, job duration, upstream errors and failure count.

Principal risks and mitigations are:

| Risk | Consequence | Mitigation |
|---|---|---|
| Cloud-contaminated Sentinel-2 periods | False water/vegetation signal | SCL mask, narrow composites, valid-fraction threshold, HLS and optional Sentinel-1 fallback |
| Seasonal reservoir management mistaken for drought | Invalid causal claim | Call output "surface-water extent anomaly"; add ERA5-Land and official hydrology only as contextual evidence |
| Shoreline mixed pixels / 10–30 m resolution mismatch | Area instability | Compare at consistent grids; report threshold sensitivity; avoid false decimal precision |
| Sentinel/Landsat inconsistency | Artificial time-series jumps | Prefer HLS for harmonized series; use native Sentinel-2 mainly for 10 m mapping |
| Cloud/API service changes | Demo failure | Cache the final demo inputs/derived artifacts with legal attribution; preserve manifests; add provider adapter |
| CDSE/GEE quotas | Slow or blocked processing | Small AOIs, cache outputs, enforce request caps; do not require GEE in production |
| Romanian hydrological access unavailable | Weak independent validation | Make station data optional; use frozen visual reference samples for segmentation validation |
| Pixel leakage in ML | Inflated accuracy | Reservoir/year holdouts |
| Scope expansion into land-risk/property product | Five-week failure | Explicitly exclude zoning, property risk, insurance scoring, ground motion and LLM reports from this project |
| Misleading "drought score" | Scientific/product liability | No composite drought score in MVP; explain each observed metric and uncertainty independently |

The `Idea(1).docx` supplied by the team describes a much broader "Land Check" platform covering flood susceptibility, ground motion, land use, arability, terrain, fire and zoning. fileciteturn1file6 That may be a longer-term product direction, but it is too broad for this five-week EO masterclass. The present dossier intentionally narrows the scope to one scientifically auditable environmental-monitoring workflow.

The numerical claims contained in the slide decks, such as scene-count/download-size examples, have not been treated as authoritative unless independently verified against an official source. The course material is used here to establish project intent and methodology, while external dataset/access/licensing claims are sourced from primary provider documentation.

## PRD agent handoff

Copy the following brief into the separate PRD-writing agent.

```text
Produce a complete, implementation-ready Product Requirements Document for a five-week Romanian Space Initiative (ROSPIN) Satellite Data Processing Masterclass student project.

Product working name:
Lower Olt EO Monitor

Required technical constraints:
- Python backend.
- FastAPI + Pydantic.
- PostgreSQL/PostGIS.
- Durable background worker/queue.
- S3-compatible object storage.
- Raster processing with rasterio/rioxarray/xarray/numpy.
- STAC access with pystac-client where applicable.
- Optional rio-tiler/TiTiler for raster tile delivery.
- TypeScript + React frontend built with Vite.
- MapLibre GL JS or equivalent open map renderer.
- TanStack Query or equivalent server-state library.
- AOI drawing/select controls.
- Docker Compose local development.
- The production architecture must remain low-cost and usable with modest student cloud credits.

Product purpose:
Build a real web application for monitoring observed surface-water extent and surrounding vegetation/moisture anomalies for selected Lower Olt River reservoirs in Romania. The product uses public Earth-observation data and must expose source provenance, observation quality and reproducible exports.

Primary AOIs:
The ROSPIN masterclass specifically names Lake Ipotești, Drăgănești and Frunzaru in its Lower Olt reservoir exercise. Store reviewed AOI polygons as versioned GeoJSON rather than relying on runtime place-name geocoding.

Primary data:
1. Copernicus Sentinel-2 Level-2A via current CDSE interfaces.
2. NASA HLS L30 and S30 v2 for the harmonized historical 30 m time series.
3. Landsat 8/9 Collection 2 Level-2 as an optional cross-check.
4. CLMS Water and Wetness / CORINE as contextual layers.
5. ERA5-Land as optional meteorological context.
6. Romanian INHGA / ABA Olt records only if access and reuse terms are verified; do not make MVP completion depend on them.
7. Sentinel-1 GRD is a stretch feature and the basis for an alternative flood-mapping experiment.

Scientific constraints:
- Never claim that NDVI, NDMI or NDWI alone proves meteorological drought, crop yield, water quality or reservoir storage volume.
- Call the primary result surface-water extent or surface-water extent anomaly.
- Distinguish:
  McFeeters open-water NDWI = (Green - NIR) / (Green + NIR)
  Gao vegetation NDWI = (NIR - SWIR) / (NIR + SWIR), noting Gao's original ~1.24 µm definition
  NDMI = (NIR - SWIR1) / (NIR + SWIR1)
- Never use an ambiguous API/UI field named only "NDWI".
- Apply source-appropriate reflectance scaling before index calculations.
- Mask clouds, cloud shadows, nodata, saturated pixels, cirrus and snow/ice according to the source QA layer.
- Treat 20 m or 30 m source information honestly; resampling does not increase physical information.
- Calculate areas in a projected CRS, not raw latitude/longitude degrees.
- Use same-season historical baselines, not simple winter-versus-summer claims.
- Expose valid-pixel fraction, observation count and method/version metadata.
- If ML is added, prohibit random pixel train/test splits. Split by reservoir, region or year.
- Freeze validation reference data before final tuning.
- Include negative and ambiguous results.

Research hypothesis:
For predefined Lower Olt reservoir AOIs, a cloud-masked Sentinel-2 or HLS index-based water-extraction workflow with a season-matched historical reference will provide more stable estimates of surface-water extent than the lecture baseline Green > NIR rule when evaluated against independently inspected reference samples and, where obtainable, official hydrological observations.

Baseline:
water = Green > NIR after invalid-pixel masking.

Improved MVP method:
McFeeters NDWI open-water classification after source-appropriate reflectance scaling and cloud/shadow/nodata masking, with a fixed threshold selected before held-out evaluation and temporal compositing when required.

Required MVP user flow:
1. User opens map.
2. User selects a predefined Lower Olt reservoir or draws an AOI within allowed limits.
3. User chooses analysis date/window.
4. Backend searches source catalog.
5. Backend queues asynchronous analysis.
6. UI displays lifecycle/progress.
7. Pipeline applies QA mask and computes water map and vegetation-context indices.
8. Pipeline creates same-season historical baseline and anomaly.
9. UI displays map, water-area time series, NDVI/NDMI context, valid-pixel fraction and source metadata.
10. User downloads CSV plus georeferenced raster/GeoJSON result.
11. User can open a methodology/provenance panel explaining equations, source items, algorithm version and known limitations.

Required pages:
- Landing / purpose / limitations.
- Map and AOI selection.
- Analysis configuration.
- Results dashboard.
- Provenance / methodology / exports.

Required API:
GET /api/v1/aois
GET /api/v1/aois/{aoi_id}
POST /api/v1/analyses
GET /api/v1/analyses/{analysis_id}
GET /api/v1/analyses/{analysis_id}/timeseries
GET /api/v1/analyses/{analysis_id}/layers
GET /api/v1/analyses/{analysis_id}/exports/{format}
GET /api/v1/tiles/{layer_id}/{z}/{x}/{y}.png
GET /api/v1/catalog/search
GET /api/v1/health
GET /api/v1/version

Async lifecycle:
queued -> catalog_search -> fetching -> processing -> validating -> publishing -> succeeded
Failure states:
failed, cancelled.

Required provenance per result:
- AOI ID/version
- provider
- collection
- source item IDs
- source acquisition datetimes
- bands
- QA/mask policy
- scaling rule
- analysis CRS
- resolution
- composite type
- threshold
- valid fraction
- algorithm version
- git commit
- attribution/license text
- checksum of source manifest and generated artifacts

Initial persistence:
PostGIS tables for AOIs, analyses, source_items, observation_stats and artifacts.
Object storage prefixes:
source-manifests/
intermediate/
rasters/
exports/
fixtures/

Five-week schedule:
Week 1: source/API/auth smoke tests, AOIs, scientific contract, masks/scaling.
Week 2: complete deterministic EO processing pipeline and fixture tests.
Week 3: FastAPI jobs, PostGIS, worker, object storage and tiles.
Week 4: React map/dashboard/export UI plus frozen scientific evaluation.
Week 5: reproducibility, CI/CD, observability, accessibility, attribution, demo and final validation report.

Acceptance criteria:
- One command can query real EO source metadata for an Olt AOI.
- Results use documented QA masks.
- Baseline and improved water methods are separately reproducible.
- NDVI/NDMI are contextual and correctly labelled.
- A same-season historical baseline is displayed.
- All outputs expose valid-pixel fraction and provenance.
- A georeferenced result renders on the map.
- CSV and raster/vector exports work.
- A clean Docker Compose environment reproduces the demo.
- No UI text states that a spectral index alone proves drought, yield loss or water quality.
- No unsupported accuracy target may be invented.

Out of scope for the MVP:
- Property or mortgage risk scoring.
- Legal zoning/buildability.
- Insurance scoring.
- Ground-motion/EGMS module.
- Agricultural yield prediction.
- Water-quality estimation.
- Reservoir volume estimation without bathymetry/elevation-volume relationships.
- Nationwide processing.
- Deep-learning segmentation.
- Real-time emergency alerting.
- User authentication unless needed for deployment.
- LLM-generated environmental conclusions.

Stretch goals:
- Sentinel-1 GRD cross-sensor water/flood analysis.
- ERA5-Land meteorological context.
- Verified Romanian station-level hydrology integration.
- Multi-reservoir comparison.
- Threshold sensitivity/uncertainty view.
- User-defined AOIs.
- Galați September 2024 flood-method comparison against CEMS EMSR758.
- Only after all above: supervised ML with spatial/temporal holdouts.

Primary source URLs to preserve in the PRD:
CDSE STAC:
https://documentation.dataspace.copernicus.eu/APIs/STAC.html
https://stac.dataspace.copernicus.eu/v1/

CDSE quotas:
https://documentation.dataspace.copernicus.eu/Quotas.html

CDSE S3:
https://documentation.dataspace.copernicus.eu/APIs/S3.html

Sentinel-2 L2A:
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html

Sentinel terms:
https://dataspace.copernicus.eu/terms-and-conditions

Sentinel-1 GRD:
https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S1GRD.html

NASA HLS:
https://hls.gsfc.nasa.gov/data-access-and-tools/
https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf

HLS L30 DOI:
https://doi.org/10.5067/HLS/HLSL30.002

Landsat access:
https://www.usgs.gov/landsat-missions/landsat-data-access
https://www.usgs.gov/landsat-missions/spatiotemporal-asset-catalog-stac
https://landsatlook.usgs.gov/stac-server

Landsat scaling:
https://www.usgs.gov/faqs/how-do-i-use-a-scale-factor-landsat-level-2-science-products

Landsat QA:
https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands

CLMS data policy:
https://land.copernicus.eu/en/data-policy

CLMS Water and Wetness:
https://land.copernicus.eu/en/products/high-resolution-layer-water-and-wetness/water-and-wetness-status-2018

ERA5-Land:
https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land

INHGA:
https://www.hidro.ro/

ABA Olt:
https://olt.rowater.ro/

Copernicus EMS Galați event:
https://mapping.emergency.copernicus.eu/news/flood-in-galati-and-vaslui-counties-romania/

Google Earth Engine noncommercial tiers:
https://developers.google.com/earth-engine/guides/noncommercial_tiers
https://developers.google.com/earth-engine/guides/usage

TiTiler:
https://developmentseed.org/titiler/

pystac-client:
https://pystac-client.readthedocs.io/

All web sources were verified/accessed on 2026-11-22. Preserve citations and access date in the final PRD. Mark quota/pricing/access rules as time-sensitive.

Human decisions that must be confirmed before implementation:
- Exact reviewed polygons for Ipotești, Drăgănești and Frunzaru.
- Whether the first demo is one reservoir or all three.
- Exact calibration and held-out years/date windows after real catalog inspection.
- Whether Sentinel-2 or HLS is the canonical time-series layer in the UI.
- Fixed NDWI-water decision threshold and how it is selected without test leakage.
- Minimum valid-pixel fraction for a result to be called usable.
- Maximum AOI/date-range/job limits after performance profiling.
- Hosting provider and actual student-credit budget cap.
- Whether the team will request hydrological data from ABA Olt/INHGA.
- Whether Galați flood mapping is retained as a stretch comparison or removed entirely.
- Final product name.
```

The technical sources above were checked against current primary documentation on 22 November 2026. Time-sensitive items that should be rechecked immediately before deployment are CDSE quotas and authentication behavior, Google Earth Engine noncommercial limits, HLS known issues/latency notices, and Romanian hydrological access arrangements. CDSE currently documents a general-user free tier with explicit request, processing-unit and transfer limits, while Earth Engine's current noncommercial model uses project-level monthly EECU tiers; both are operational policies rather than permanent scientific properties. citeturn360731view2turn766839search0

Before this material is used as the final project specification, the human team should verify the AOI boundaries, live access to each chosen source, licensing/attribution text, DOI resolution, scientific threshold choices and deployment budget; the resulting PRD/edit history should disclose AI assistance and human verification.