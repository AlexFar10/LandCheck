# Step-by-step guide: downloading satellite data for Pechea (Galați)

Updated on 25 November 2026. This guide holds the exact steps of the first download, in the order they were done, with the final working code (including the fixes). Anyone on the team can redo everything from scratch, on a Mac.

**Area:** Pechea, Galați County, where the flood of 13–14 September 2024 happened.
- Working rectangle (west, south, east, north): `27.6159, 45.4607, 27.8670, 45.7384`. It is about 25 × 30 km.
- The village of Pechea is at about lat 45.63, lon 27.80.
- The metric projection used everywhere: UTM zone 35N (`EPSG:32635`).

**Basic idea:** we do not download whole archives. Each source is cut to the Pechea area and to the period we care about. Everything together is about **800 MB**, of which about 450 MB are the EGMS tiles (Step 7). Without EGMS it is about 340 MB.

**Where the data goes:** in `data/`, at the root of the repo. The `data/` folder is ignored by git (`.gitignore`) because it is too large. Only processed data goes in `datasets/`.

**What comes after:** the scripts that turn this data into the dataset and the risk modules are explained in `GUIDE_PECHEA_SCRIPTS.md`.

---

## Words you will meet

- **Sentinel-1**: radar satellite. It sees through clouds and at night. Water shows up black.
- **Sentinel-2**: satellite that takes ordinary (optical) pictures. It cannot see through clouds.
- **CEMS**: the European service that makes maps of flooded areas after a disaster.
- **JRC Global Surface Water**: a map of the places where there is usually water (from 1984 on).
- **DEM**: the map of the terrain's elevation.
- **EGMS**: a European map of how much the ground rises or sinks (mm/year), measured from radar.
- **ANM**: the Romanian National Meteorological Administration. Here, daily rainfall.
- **EOCube**: the Romanian data platform (UVT). The data there is open source.
- **Earth Engine**: Google's platform where you view and process images directly in the browser.
- **STAC**: an online catalogue of images, where you search by area and date.
- **GeoTIFF (.tif)**: an image that knows where it sits on the map.

---

## Step 1. CEMS flood maps (no account, ~2 minutes)

**What they are:** ready-made maps from the European Union showing the flooded areas at Pechea on 14, 15 and 17 September 2024.

1. Open **Terminal**.
2. Go to the project folder:
```bash
cd <repo-folder>
```
3. Run the lines below, one at a time:
```bash
mkdir -p data/cems
cd data/cems
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/FEP_PRODUCT/EMSR758_AOI03_FEP_PRODUCT_v1.zip
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/DEL_PRODUCT/EMSR758_AOI03_DEL_PRODUCT_v1.zip
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/DEL_MONIT01/EMSR758_AOI03_DEL_MONIT01_v1.zip
ls -lh
```

**What you see:** 3 `.zip` files, of 2.2 MB, 5.3 MB and 8.1 MB.

**Verified result:** the checksums match the ones in the PRD exactly:
```
95e81d5839d3fd8b24ebb68651bc7f3b349168ac04847204a8e3dadc36df133b  EMSR758_AOI03_FEP_PRODUCT_v1.zip
8cb85940a59291147b11dbe9dfd5be75c37d37e1c061c1832a531cb543d7642e  EMSR758_AOI03_DEL_PRODUCT_v1.zip
c5f662293b7cfb977504bf84335c25218e65b4786e78baed4bd1444a3b6e1eb5  EMSR758_AOI03_DEL_MONIT01_v1.zip
```
To check: `shasum -a 256 *.zip`.

What each one holds:
- **FEP**: 14 Sep 2024, 04:22, from Sentinel-1.
- **DEL**: 15 Sep, from the PAZ satellite.
- **MONIT01**: 17 Sep, from COSMO-SkyMed.

In each ZIP, the `observedEventA` layer holds the polygons of the flooded area. They open in QGIS.

---

## Step 2. The radar image on the day of the flood, in Earth Engine (viewing)

**What it is:** Sentinel-1 images from 2 September (before) and 14 September (the day of the flood). Both come from the same orbit (109), so they can be compared. The 14 September image is the very one CEMS used for the FEP map.

1. Open **code.earthengine.google.com** and log in with the Google account registered for Earth Engine.
2. Delete everything in the middle editor, paste the code below and press **Run**.

```javascript
// Pechea area
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);

// Sentinel-1 radar images over the area, same satellite position (orbit 109)
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(zona)
  .filter(ee.Filter.eq('relativeOrbitNumber_start', 109))
  .select('VV');

var inainte = s1.filterDate('2024-09-02', '2024-09-03').first().clip(zona);
var inundatie = s1.filterDate('2024-09-14', '2024-09-15').first().clip(zona);

Map.centerObject(zona, 11);
Map.addLayer(inainte, {min: -25, max: 0}, 'Before: 2 Sep 2024');
Map.addLayer(inundatie, {min: -25, max: 0}, 'Flood: 14 Sep 2024');
```

**What you see:** two black-and-white images appear on the map. **Water is black.** From the **Layers** button (top right of the map) you switch each image on and off. In the 14 September image there are long black stripes in the valleys that were not there on 2 September. That is where the flood was.

IDs of the scenes used:

| Role | Scene ID | Acquired (UTC) | Orbit |
|---|---|---|---|
| Day of the flood | `S1A_IW_GRDH_1SDV_20240914T042150_20240914T042215_055656_06CBAD_DE46` | 2024-09-14 04:21:50 | descending, 109 |
| Before | `S1A_IW_GRDH_1SDV_20240902T042150_20240902T042215_055481_06C4C3_060D` | 2024-09-02 04:21:50 | descending, 109 |

There are two more scenes, not used for now:
- 15 Sep 2024, 16:09, ascending, orbit 131. Its "before" pair is from 3 Sep.
- 26 Sep 2024, 04:21, descending, orbit 109. It shows the area after the water withdrew.

---

## Step 3. Downloading the radar images to your computer

1. **Add the lines below at the end of the code** in the editor and press **Run**:
```javascript
Export.image.toDrive({
  image: inainte, description: 'pechea_s1_inainte_2024-09-02',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9
});
Export.image.toDrive({
  image: inundatie, description: 'pechea_s1_inundatie_2024-09-14',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9
});
```
2. In the panel at the top right, the **Tasks** tab, press **RUN** on each row, then **Run** once more in the window that appears. Change nothing there.
3. After 1–3 minutes the rows turn blue, with a tick.
4. Open **Google Drive** and go into the `landcheck` folder. Download the 2 `.tif` files.
5. Move them to `data/s1/`.

The format is GeoTIFF, which is the right one.

**Verified result:** 2 files of 57 MB each. They hold the VV band in dB, at 10 m. Water is around −18 dB or lower.

---

## Step 4. Permanent water (JRC) and relief (DEM), from Earth Engine

**What they are for:**
- **Permanent water (JRC)** shows where there is always water, so that you do not count the river or the lakes as flooding.
- **Relief (DEM)** shows the elevation of each point. Water gathers in the low areas.

1. **Delete only the 2 `Export.image.toDrive(...)` blocks from Step 3.** Keep the rest of the code, especially `var zona = ...`.
2. Add the code below at the end and press **Run**:
```javascript
// Permanent water: in what % of the observations since 1984 there was water (0–100)
var apa = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0).clip(zona);
Map.addLayer(apa, {min: 0, max: 100, palette: ['white', 'blue']}, 'JRC permanent water');

// Relief: elevation in metres
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(zona)
  .select('DEM').mosaic().clip(zona);
Map.addLayer(dem, {min: 0, max: 250, palette: ['green', 'yellow', 'brown']}, 'DEM relief');

Export.image.toDrive({image: apa, description: 'pechea_jrc_apa_permanenta',
  folder: 'landcheck', region: zona, scale: 30, crs: 'EPSG:32635', maxPixels: 1e9});
Export.image.toDrive({image: dem, description: 'pechea_dem_relief',
  folder: 'landcheck', region: zona, scale: 30, crs: 'EPSG:32635', maxPixels: 1e9});
```
3. In **Tasks**, press **RUN** on the 2 new rows.
4. Download the files from Drive into `data/context/`.

The yellow message "This asset is deprecated" for the DEM can be ignored. The data is correct.

**Verified result:**
- `pechea_dem_relief.tif` (2.8 MB): elevations between 5 and 168 m, with a mean of 62 m. Only ~2% empty pixels, at the edges.
- `pechea_jrc_apa_permanenta.tif` (15 KB): small, because the area is almost all dry land. Permanent water covers ~0.4% of the area. This is JRC version 1.4, with data up to 2021. In Step 8 we replace it with the newer version from EOCube.

---

## Step 5. Sentinel-2 pictures before and after (Earth Engine)

**What they are:** ordinary satellite pictures. The code takes all the pictures in the period, removes the clouds, and combines them into one clean image for each period:
- **Before:** 15 Aug – 11 Sep 2024.
- **After:** 15 Sep – 5 Oct 2024.

1. Delete everything in the editor, paste the full code below and press **Run**.

```javascript
// Pechea area
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);
Map.centerObject(zona, 11);

// ---------- Sentinel-1 radar (orbit 109) ----------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(zona)
  .filter(ee.Filter.eq('relativeOrbitNumber_start', 109))
  .select('VV');
var inainte = s1.filterDate('2024-09-02', '2024-09-03').first().clip(zona);
var inundatie = s1.filterDate('2024-09-14', '2024-09-15').first().clip(zona);
Map.addLayer(inainte, {min: -25, max: 0}, 'Radar before: 2 Sep 2024', false);
Map.addLayer(inundatie, {min: -25, max: 0}, 'Radar flood: 14 Sep 2024', false);

// ---------- JRC permanent water (0–100 %) ----------
var apa = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0).clip(zona);
Map.addLayer(apa, {min: 0, max: 100, palette: ['white', 'blue']}, 'JRC permanent water', false);

// ---------- DEM relief (metres) ----------
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(zona)
  .select('DEM').mosaic().clip(zona);
Map.addLayer(dem, {min: 0, max: 250, palette: ['green', 'yellow', 'brown']}, 'DEM relief', false);

// ---------- Sentinel-2 pictures, without clouds ----------
function faraNori(img) {
  var scl = img.select('SCL');
  var curat = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(curat).divide(10000).copyProperties(img, ['system:time_start']);
}
function pozaCurata(start, end) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zona).filterDate(start, end)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
    .map(faraNori).select(['B4', 'B3', 'B2', 'B8'])   // red, green, blue, near-infrared
    .median().clip(zona);
}
var s2Inainte = pozaCurata('2024-08-15', '2024-09-11');
var s2Dupa    = pozaCurata('2024-09-15', '2024-10-05');

var culori = {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3};
Map.addLayer(s2Inainte, culori, 'Picture before');
Map.addLayer(s2Dupa, culori, 'Picture after');

// ---------- Export (Sentinel-2 only) ----------
Export.image.toDrive({image: s2Inainte.toFloat(), description: 'pechea_s2_inainte',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9});
Export.image.toDrive({image: s2Dupa.toFloat(), description: 'pechea_s2_dupa',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9});
```

2. Look on the map at "Picture before" and "Picture after". The layers from Steps 2–4 are there too, but hidden. You switch them on from **Layers**.
3. In **Tasks**, press **RUN** on `pechea_s2_inainte` and `pechea_s2_dupa`.
4. Be patient: Sentinel-2 exports take **5–20 minutes**, because dozens of pictures are combined. It is a problem only if it goes past 30 minutes or turns red.
5. Download the files from Drive into `data/s2/`.

**Fix compared with the first version.** The first version of the code gave the error "Can't get band number 0. Image has no bands". Cause: the function that removes the clouds lost the date of each picture, so the date filter found nothing. The code above fixes it in two ways:
- the function uses `.copyProperties(img, ['system:time_start'])`, so it keeps the date;
- the date filter is applied before the clouds are removed.

**Verified result:**
- 2 files, of 81 MB (before) and 75 MB (after).
- Each has 4 bands (B4, B3, B2, B8), 1988 × 3104 pixels of 10 m, with only ~2% empty pixels at the edges.
- The values are real reflectance, around 0.1–0.2. Earth Engine already applies the −1000 correction in the `HARMONIZED` collection.

---

## Step 6. ANM rainfall, with Python, from EOCube (no account)

**What it is:** daily rainfall measured by ANM, on a grid of ~1 km, from 1961 on. The whole cube is **185 GB**. The script reads only September 2024 over Pechea, that is 30 days × 28 × 25 cells.

### 6a. Python setup (once)

In Terminal:
```bash
python3 --version
```
It may show, for example, `Python 3.14.8`. Then:
```bash
cd <repo-folder>/data/cems
python3 -m venv .venv
source .venv/bin/activate
pip install xarray zarr aiohttp requests fsspec pandas
```
The Python environment (`.venv`) ended up in the `data/cems` folder. It works the same from anywhere. (For the project's code, a separate `.venv` at the repo root is used, see `GUIDE_PECHEA_SCRIPTS.md`.)

**When you reopen Terminal**, always run first:
```bash
cd <repo-folder>/data
source cems/.venv/bin/activate
```
At the start of the line `(.venv)` must appear.

### 6b. The rainfall script

From the `data` folder, create the script by pasting the whole block at once:
```bash
cat > anm_ploaie.py << 'EOF'
import os
import xarray as xr

URL = "https://storage.svc.uvt-01.eocube.ro/meteo/cube/open-v1/"
VEST, SUD, EST, NORD = 27.6159, 45.4607, 27.8670, 45.7384

ds = xr.open_zarr(URL, consolidated=True)
print(ds)  # shows which variables and axes the cube has

# find the axis names (they can be lon/lat or x/y)
xn = next(n for n in ("lon", "longitude", "x") if n in ds.dims)
yn = next(n for n in ("lat", "latitude", "y") if n in ds.dims)
y = ds[yn]
ysl = slice(SUD, NORD) if float(y[0]) < float(y[-1]) else slice(NORD, SUD)

p = ds["precipitation"].sel(time=slice("2024-09-01", "2024-09-30"))
p = p.sel({xn: slice(VEST, EST), yn: ysl}).load()
print("Cells in the area:", p.sizes)

zilnic = p.mean([xn, yn]).to_series().round(1)
os.makedirs("anm", exist_ok=True)
zilnic.to_csv("anm/ploaie_medie_pechea_sep2024.csv", header=["mm"])
p.to_dataframe().reset_index().to_csv("anm/ploaie_grid_pechea_sep2024.csv", index=False)

print("\nAverage rain over the Pechea area (mm/day):")
print(zilnic.to_string())
print("\nTotal 10-16 Sep:", round(zilnic["2024-09-10":"2024-09-16"].sum(), 1), "mm")
EOF
```
Then run it:
```bash
python3 anm_ploaie.py
```

**What you see:** the description of the cube (185 GB, axes `x` and `y`, from 1961 to 2050), then `Cells in the area: time 30, y 28, x 25` and the rain for each day.

**Verified result** (average over the Pechea area):

| Day | mm |
|---|---|
| 6–7 Sep | 4.6 and 8.1 |
| **12 Sep** | **17.4** |
| 13 Sep | 0.5 |
| **14 Sep** | **57.4** |
| 15 Sep | 1.7 |
| **16 Sep** | **31.2** |
| 18 Sep | 4.8 |
| 30 Sep | 15.8 |
| **Total 10–16 Sep** | **108.2 mm** |

Files created:
- `data/anm/ploaie_medie_pechea_sep2024.csv`, with the average per day;
- `data/anm/ploaie_grid_pechea_sep2024.csv`, with every cell.

Watch out for two things:
- At ANM a rain "day" is usually measured from 06:00 to 06:00 the next day. The value for 14 Sep may therefore also include the night from 13 to 14 Sep.
- Days not yet written in the cube show up as 0, not as missing. For recent periods, check `last_precipitation_time` first.

The grid file is also used by the code (`flood_context.py`): it takes the cell nearest the parcel, whose values can differ a lot from the area average (for example 14 Sep: 27 mm in one cell, 64 mm in another).

---

## Step 7. Ground movement, EGMS (EU Login account, free)

**What it is:** how much the ground rises or sinks (mm/year), measured from radar between 2020 and 2025.

EGMS gives the data on **100 km tiles**. You cannot download "just Pechea". The Explorer selects the whole tiles that your polygon touches. A script (7c) then cuts out the Pechea zone.

### 7a. Log in and find the place

1. Go to **https://egms.land.copernicus.eu/**.
2. **Login:** it is not a written button but a **padlock icon** 🔒 in the toolbar (the last button, bottom of the vertical bar on a narrow window). Direct link: https://egms.land.copernicus.eu/login. If you have no account, press **Create an account** and confirm by email.
3. In the box at the top left type the coordinates, **latitude first**: `45.6228 27.8436`, and press Enter. The map jumps to Pechea and puts a blue dot there.
4. Open the layer list (the ☰ icon), then **ORTHO (Level 3)**, and switch on **Vertical 2020-2025**.
5. **Background map:** if the map is black, the site shows a message that the default background is down for maintenance. In the layer list, open **Background Layers** and choose **OpenStreetMap Composite**.
6. **What you see:** small green dots on a dark background. They appear only in strips, on villages, roads, buildings and bare ground, where the radar gets a stable echo. Fields have almost no points. The blue dot at Pechea may sit in such an empty spot. That is normal.

### 7b. Download the tiles

1. Zoom out until you see a scale of about 5 km.
2. In the toolbar press the **polygon with arrow** button (Product Archive). Draw a rectangle around Pechea by clicking, and close it with a double click.
3. A **Product Archive** window opens. Choose the level **Ortho**, and run the search.
4. Next to the **Download** button (arrow pointing down) a number appears: the files found. Press **Download**. Download links appear, one per file. (The manual also describes a button that saves all the links in one text file.)
5. The links expire after one hour. Download them in that time.
6. The site selects the tiles on its own. For Pechea we got **4 files**: two tiles (`E56N26` and `E57N26`), each with the vertical component (`U`) and the east-west component (`E`):
```
EGMS_L3_E56N26_100km_U_2020_2025_1.zip
EGMS_L3_E56N26_100km_E_2020_2025_1.zip
EGMS_L3_E57N26_100km_U_2020_2025_1.zip
EGMS_L3_E57N26_100km_E_2020_2025_1.zip
```
7. Unzip each archive into `data/egms/`. Each one becomes a folder with the same name, holding a `.csv` (the points), a `.tiff` (the image) and an `.xml` (metadata). In total about **450 MB**.

**Verified result:**
- The tile name is the lower-left corner of a 100 km square in the European projection (EPSG:3035): `E56N26` = 5,600 km east, 2,600 km north. **Pechea is in tile `E56N26`**; `E57N26` covers the east.
- Each CSV has **one row per radar point**: `pid`, `easting`, `northing` (EPSG:3035), `height_ortho`, `mean_velocity` (mm/year), `acceleration`, and the time series from 9 Dec 2020 to 25 Nov 2025. About 317 columns.
- The tile `E56N26` has **94,570 points**. **612 of them are within 2 km** of the coordinates above, the nearest 9 m away. Median vertical velocity in that circle: **−0.6 mm/year**.
- Tile `E56N26`: the vertical and east-west components use the same point IDs, so they can be joined.

### 7c. Cutting the Pechea zone (script in the repo)

The 4 CSVs are too big to keep in git. The script `landcheck/ingest/egms.py` keeps only the points in the pilot zone (the CEMS coverage plus 5 km), joins vertical and east-west, converts the coordinates to lat/lon and writes a small file. It also records the checksums of the 4 CSVs. Run it from the repo root, with the project's `.venv` active:
```bash
python -m landcheck.ingest.egms --raw data/egms \
  --coverage datasets/pilot-pechea/v1/coverage.geojson \
  --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv \
  --average data/egms/egms_pechea_medie_508_vertical.txt \
  --average data/egms/egms_pechea_east_west.txt
```
**Result:** `14608 points kept, median vertical -0.6 mm/yr`. The `--average` options are the optional cross-check from 7d. The script needs `datasets/pilot-pechea/v1` (made by `landcheck.ingest.cems`, see `GUIDE_PECHEA_SCRIPTS.md`).

### 7d. Optional: area averages copied from the Explorer (cross-check)

Before we found the tile download, we took the area averages by hand. They are still useful as a check that the tile data is right. In the Explorer:
1. Select an area around Pechea with the mouse. A window with a chart opens, for example "Average of 508 points".
2. From the menu at the top left of the window choose the series, for example "1. Vertical: Average of 508 points".
3. Press **View Data**. There is no download button, it is done by copying: click in the table, then **Cmd+A** and **Cmd+C**.
4. In Terminal, from the `data` folder:
```bash
mkdir -p egms && pbpaste > egms/egms_pechea_medie_508_vertical.txt && head -3 egms/egms_pechea_medie_508_vertical.txt
```
On the second line it must say `Dataset Vertical`. Repeat for East/West, with `pbpaste > egms/egms_pechea_east_west.txt`.
5. **Generate SVG**, in the same window, saves the chart as an image. Move it to `data/egms/`.

**Verified result:**
- **Average of the 508 points, vertical:** `egms_pechea_medie_508_vertical.txt`, 303 measurements between 9 Dec 2020 and 25 Nov 2025. `mean_velocity` in the header: **−0.70 mm/year**. The slope recomputed from the data: −0.69 mm/year. The ground sank about 3.3 mm in total in 5 years. It is **stable**, under the project's thresholds: −2 mm/year for "medium" and −5 mm/year for "high".
- **Average of the 559 points, east-west:** `egms_pechea_east_west.txt`, `mean_velocity` 0.03 mm/year, so no lateral movement.
- The number of points in the average differs (559 and 508) because it depends on the area selected with the mouse.
- **Cross-check with the tiles** (the report written by the script in 7c): the mean of the nearest 508 points is −0.702 mm/year, against −0.698 in the Explorer (difference 0.004). East-west: 0.043 against 0.031. The tile data and the Explorer agree.

Conclusion for the application: "Ground movement at Pechea: stable, about −0.7 mm/year (average of ~500 EGMS points, 2020–2025)." For one specific parcel the app uses the points near it, and says "No coverage" if there are none.

---

## Step 8. New permanent water (JRC v1.5), from EOCube

**Why:** it is the same permanent-water map as in Step 4, but the newer version, with data **up to 2024**. The one in Earth Engine only has data up to 2021. It also comes from EOCube, the team's platform.

1. From the `data` folder, with `(.venv)` active:
```bash
pip install pystac-client odc-stac rioxarray
```
2. Create the script (paste the whole block):
```bash
cat > eocube_jrc.py << 'EOF'
import rioxarray
from pystac_client import Client
import odc.stac
from shapely.geometry import box

zona = box(27.6159, 45.4607, 27.8670, 45.7384)
cat = Client.open("https://stac.eocube.ro")
items = list(cat.search(collections=["jrc-gsw-v1-5-occurrence"], intersects=zona).items())

# the files are on EOCube storage: we read them over HTTPS, as for ANM
for it in items:
    for a in it.assets.values():
        if a.href.startswith("s3://"):
            a.href = a.href.replace("s3://", "https://storage.svc.uvt-01.eocube.ro/")
print("File:", items[0].assets["occurrence"].href)

data = odc.stac.load(items, geopolygon=zona, crs="EPSG:32635", resolution=30, bands=["occurrence"])
data["occurrence"].isel(time=0).rio.to_raster("context/pechea_jrc_occurrence_v1_5_eocube.tif")
print("Saved: context/pechea_jrc_occurrence_v1_5_eocube.tif")
EOF
```
3. Run:
```bash
python3 eocube_jrc.py
```

**What you see:** the line `File: https://storage.svc.uvt-01.eocube.ro/jrc-gsw-v1-5/...occurrence_20E_50N_v1_5_2024.tif`, then `Saved: ...`.

**Fixes compared with the first version** (they showed up as errors along the way):
1. The error `InvalidCredentials: No valid AWS credentials found`. In the catalogue, the EOCube files have `s3://...` addresses, which need an account. The script turns them into `https://storage.svc.uvt-01.eocube.ro/...` addresses, which work without an account.
2. The error `'DataArray' object has no attribute 'rio'`. `import rioxarray` was missing at the top of the script.

**Verified result:**
- `context/pechea_jrc_occurrence_v1_5_eocube.tif` (673 KB): the same grid as in Step 4, 664 × 1035 pixels of 30 m.
- The values are between 0 and 95%. Permanent water (more than 50% of the time) covers **0.44%** of the area, against 0.40% in the old version.

From now on this file is used. The old one (`pechea_jrc_apa_permanenta.tif`) stays only as a backup.

The same script works for any EOCube collection. You only change the collection name and the band, for example `jrc-gsw-v1-5-monthlyhistory`, which has water month by month, including September 2024.

---

## Step 9. Land use over time (landuse): summer NDVI, 2018–2025

**What it is:** NDVI is a number from −1 to 1 that shows how green the vegetation is. Close to 1 means dense vegetation, close to 0 means bare ground, a road or buildings. A cultivated field changes its NDVI from year to year and during the year, a forest stays green, and built-up land always stays without green. From NDVI you can infer how the land was used. Here we make one image per year, only for summer (June–August), from 2018 on. Before 2018, Sentinel-2 has few corrected images over Europe.

1. In Earth Engine delete everything in the editor, paste the code below and press **Run**.

```javascript
// Pechea area
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);
Map.centerObject(zona, 11);

function faraNori(img) {
  var scl = img.select('SCL');
  var curat = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(curat).copyProperties(img, ['system:time_start']);
}

// Mean NDVI over summer (June–August) for one year
function ndviVara(an) {
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zona)
    .filterDate(an + '-06-01', an + '-08-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
    .map(faraNori);
  print(ee.String('Pictures used in ' + an + ': ').cat(ee.Number(col.size()).format()));
  return col.map(function(img) { return img.normalizedDifference(['B8', 'B4']); })
    .median().clip(zona).rename('NDVI_' + an);
}

var ani = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
var ndviAni = ee.Image.cat(ani.map(ndviVara));

var paleta = {min: 0, max: 0.9, palette: ['brown', 'yellow', 'green', 'darkgreen']};
Map.addLayer(ndviAni.select('NDVI_2018'), paleta, 'NDVI summer 2018');
Map.addLayer(ndviAni.select('NDVI_2024'), paleta, 'NDVI summer 2024');

Export.image.toDrive({image: ndviAni.toFloat(), description: 'pechea_ndvi_vara_2018_2025',
  folder: 'landcheck', region: zona, scale: 20, crs: 'EPSG:32635', maxPixels: 1e9});
```

2. **What you see:** in the **Console** panel the numbers of pictures used for each year appear. On the map, from **Layers**, you switch on "NDVI summer 2018" and "NDVI summer 2024". Dark green is dense vegetation, yellow and brown are bare or harvested ground.
3. In **Tasks** press **RUN** on `pechea_ndvi_vara_2018_2025`, then **Run** in the window that appears. Download from Google Drive a single `.tif` file, not a zip, and put it in `data/landuse/`.

**About the yellow warning from `print`.** The first version had `print('Poze folosite in ' + an + ':', col.size())` and the editor showed "print() called with too many arguments". It is only a warning, not an error, and the code ran anyway. The version above no longer has the warning, but I did not test it separately in Earth Engine.

**Verified result:**
- `landuse/pechea_ndvi_vara_2018_2025.tif` (52 MB): 8 bands (`NDVI_2018` … `NDVI_2025`), 995 × 1553 pixels of 20 m, in `EPSG:32635`. Only ~2% empty pixels, at the edges.
- Median NDVI over the whole area, by year: 2018: 0.56, 2019: 0.55, 2020: 0.30, 2021: 0.65, 2022: 0.33, 2023: 0.43, 2024: 0.24, 2025: 0.39. The values are between −0.5 and 0.93.

**Careful with the interpretation:** the large differences from one year to the next (for example 2021 against 2024) probably come mostly from the weather (drought, heat waves) and from what was cultivated that year, but that is an assumption, I did not check it. A low NDVI in one year does not mean the land changed its use. For that you have to compare several years and several months, and the number of pictures in the Console shows how solid each image is.

---

## What you have at the end

```
data/                                      (~800 MB, not in git)
├── cems/       3 CEMS ZIPs: the flood on 14, 15 and 17 Sep 2024   (+ .venv, the Python environment)
├── s1/         radar 2 Sep and 14 Sep 2024 (VV, dB, 10 m)
├── s2/         pictures before and after (B4, B3, B2, B8, reflectance, 10 m)
├── context/    JRC v1.5 EOCube (to use), JRC v1.4 (backup), DEM 30 m
├── anm/        daily rain, September 2024 (average and grid)
├── egms/       ground movement 2020–2025
│   ├── EGMS_L3_E56N26_100km_U_2020_2025_1/   (and _E_, and the same for E57N26): csv + tiff + xml, ~450 MB in total
│   └── egms_pechea_*.txt, *.svg              (Explorer averages and charts, for cross-checking)
├── landuse/    summer NDVI by year, 2018–2025 (one file with 8 bands, 20 m)
├── anm_ploaie.py
└── eocube_jrc.py
```

**Checksums (SHA-256)** for the large files:
```
ad7341dded5d239e833748c4df2497936905c58949acefeb102410553a2f4768  s1/pechea_s1_inainte_2024-09-02.tif
07bb05643baf61fbaf83e1851882bc46446760d8aee6901d4790afb4954365b4  s1/pechea_s1_inundatie_2024-09-14.tif
2d0c61d4e10e6ddd57c76ccf3924401ff19cc55f5f7b81a691b2611e3e04b234  s2/pechea_s2_inainte.tif
3aa465f02f207bb76d3d4b20b3a089a70a93f8dc4efb349c4d52095a77e5453a  s2/pechea_s2_dupa.tif
e11d7dd453c1124a5e50cf7916e90d3dc1f520bc4943c8ef45cb9ac072abd0bf  context/pechea_jrc_occurrence_v1_5_eocube.tif
e50c4e5c10b3b596f577a20e0bb1d4add7628857725496ee328cb064c690bfde  context/pechea_dem_relief.tif
7f9268460dc0d38180046ac8e4a28da479662d801f4604b5542c04d576a5f4b3  landuse/pechea_ndvi_vara_2018_2025.tif
29f6492c6fa59f533ff8fcd7205a1113139aa51f57e672677dcf98934cd2989a  egms/egms_pechea_medie_508_vertical.txt
```
The checksums of the Earth Engine files will not be identical if you export them again. The content is the same, but the generated file differs slightly. The checksums of the EGMS tiles are recorded by the script in 7c, in the file `datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv.ingest.json`.

## What we did not take, and why

| Data | Why not |
|---|---|
| DEM from EOCube (`copernicus-dem-30`) | It is exactly the same DEM we already have from Earth Engine |
| JRC `extent` and `recurrence` from EOCube | Poorer information, or not needed now |
| JRC `monthlyhistory` | Optional. It can be taken with the script from Step 8 |
| Sentinel-1 from EOCube | EOCube has no radar images for 10–20 Sep 2024 |
| Data straight from dataspace.copernicus.eu | We took the same Copernicus images more simply through Earth Engine |
| Land-use history before 2018 | Corrected Sentinel-2 (L2A) has few images over Europe before 2018 |
| Copying the EGMS points one by one | No longer needed: the tile download gives all the points |
| ML model | We have a single event. A model needs many floods from many areas to learn something correct |

## Related documents

- `GUIDE_PECHEA_SCRIPTS.md`: what the ingest scripts and modules do with this data, file by file.
- `PRD.md`, section 7: data sources, pins and ingest rules.
