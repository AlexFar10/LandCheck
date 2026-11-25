# Ghid pas cu pas: descărcarea datelor satelitare pentru Pechea (Galați)

Actualizat pe 25 noiembrie 2026. Ghidul conține exact pașii făcuți la prima descărcare, în ordinea în care au fost făcuți, cu codul final care a mers (inclusiv corecturile). Oricine din echipă poate reface totul de la zero, pe un Mac.

**Zona:** Pechea, județul Galați, unde a fost inundația din 13–14 septembrie 2024.
- Dreptunghiul de lucru (vest, sud, est, nord): `27.6159, 45.4607, 27.8670, 45.7384`. Are cam 25 × 30 km.
- Satul Pechea e la aproximativ lat 45.63, lon 27.80.
- Proiecția metrică folosită peste tot: UTM zona 35N (`EPSG:32635`).

**Ideea de bază:** nu descărcăm arhive întregi. Fiecare sursă e tăiată pe zona Pechea și pe perioada care ne interesează. Totul la un loc are aproximativ **340 MB**.

**Unde se pun datele:** în `data/`, în rădăcina repo-ului. Folderul `data/` e ignorat de git (`.gitignore`), pentru că e prea mare. Doar datele procesate merg în `datasets/`.

---

## Cuvinte pe care le vei întâlni

- **Sentinel-1**: satelit radar. Vede prin nori și noaptea. Apa apare neagră.
- **Sentinel-2**: satelit care face poze obișnuite (optice). Nu vede prin nori.
- **CEMS**: serviciul european care face hărți ale zonelor inundate după un dezastru.
- **JRC Global Surface Water**: hartă cu locurile unde e apă de obicei (din 1984 încoace).
- **DEM**: harta altitudinii terenului.
- **EGMS**: hartă europeană cu cât se ridică sau coboară terenul (mm/an), măsurat din radar.
- **ANM**: Administrația Națională de Meteorologie. Aici, ploaia zilnică.
- **EOCube**: platforma românească de date (UVT). Datele de acolo sunt open source.
- **Earth Engine**: platforma Google unde vezi și procesezi imagini direct în browser.
- **STAC**: catalog online de imagini, în care cauți după zonă și dată.
- **GeoTIFF (.tif)**: imagine care știe unde se află pe hartă.

---

## Pasul 1. Hărțile inundației CEMS (fără cont, ~2 minute)

**Ce sunt:** hărți gata desenate de Uniunea Europeană cu zonele inundate la Pechea pe 14, 15 și 17 septembrie 2024.

1. Deschide **Terminal**.
2. Intră în folderul proiectului:
```bash
cd <folderul-repo-ului>
```
3. Rulează rândurile de mai jos, unul câte unul:
```bash
mkdir -p data/cems
cd data/cems
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/FEP_PRODUCT/EMSR758_AOI03_FEP_PRODUCT_v1.zip
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/DEL_PRODUCT/EMSR758_AOI03_DEL_PRODUCT_v1.zip
curl -fLO https://rapidmapping.emergency.copernicus.eu/backend/EMSR758/AOI03/DEL_MONIT01/EMSR758_AOI03_DEL_MONIT01_v1.zip
ls -lh
```

**Ce vezi:** 3 fișiere `.zip`, de 2,2 MB, 5,3 MB și 8,1 MB.

**Rezultat verificat:** checksum-urile se potrivesc exact cu cele din PRD:
```
95e81d5839d3fd8b24ebb68651bc7f3b349168ac04847204a8e3dadc36df133b  EMSR758_AOI03_FEP_PRODUCT_v1.zip
8cb85940a59291147b11dbe9dfd5be75c37d37e1c061c1832a531cb543d7642e  EMSR758_AOI03_DEL_PRODUCT_v1.zip
c5f662293b7cfb977504bf84335c25218e65b4786e78baed4bd1444a3b6e1eb5  EMSR758_AOI03_DEL_MONIT01_v1.zip
```
Pentru verificare: `shasum -a 256 *.zip`.

Ce conține fiecare:
- **FEP**: 14 sep 2024, 04:22, din Sentinel-1.
- **DEL**: 15 sep, din satelitul PAZ.
- **MONIT01**: 17 sep, din COSMO-SkyMed.

În fiecare ZIP, stratul `observedEventA` conține poligoanele zonei inundate. Se deschid în QGIS.

---

## Pasul 2. Imaginea radar din ziua inundației, în Earth Engine (vizualizare)

**Ce e:** imagini Sentinel-1 de pe 2 septembrie (înainte) și de pe 14 septembrie (ziua inundației). Ambele sunt de pe aceeași orbită (109), ca să fie comparabile. Imaginea din 14 septembrie e chiar cea folosită de CEMS pentru harta FEP.

1. Deschide **code.earthengine.google.com** și loghează-te cu contul Google înregistrat la Earth Engine.
2. Șterge tot din editorul din mijloc, lipește codul de mai jos și apasă **Run**.

```javascript
// Zona Pechea
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);

// Imagini radar Sentinel-1 peste zonă, aceeași poziție a satelitului (orbita 109)
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(zona)
  .filter(ee.Filter.eq('relativeOrbitNumber_start', 109))
  .select('VV');

var inainte = s1.filterDate('2024-09-02', '2024-09-03').first().clip(zona);
var inundatie = s1.filterDate('2024-09-14', '2024-09-15').first().clip(zona);

Map.centerObject(zona, 11);
Map.addLayer(inainte, {min: -25, max: 0}, 'Inainte: 2 sep 2024');
Map.addLayer(inundatie, {min: -25, max: 0}, 'Inundatie: 14 sep 2024');
```

**Ce vezi:** pe hartă apar două imagini alb-negru. **Apa e neagră.** Din butonul **Layers** (dreapta sus pe hartă) pornești și oprești fiecare imagine. În imaginea din 14 septembrie apar dungi negre lungi pe văi, care pe 2 septembrie nu erau. Acolo a fost inundația.

ID-urile scenelor folosite:

| Rol | ID scenă | Achiziție (UTC) | Orbită |
|---|---|---|---|
| Ziua inundației | `S1A_IW_GRDH_1SDV_20240914T042150_20240914T042215_055656_06CBAD_DE46` | 2024-09-14 04:21:50 | descendentă, 109 |
| Înainte | `S1A_IW_GRDH_1SDV_20240902T042150_20240902T042215_055481_06C4C3_060D` | 2024-09-02 04:21:50 | descendentă, 109 |

Mai există două scene, neluate deocamdată:
- 15 sep 2024, 16:09, ascendentă, orbita 131. Perechea ei de dinainte e din 3 sep.
- 26 sep 2024, 04:21, descendentă, orbita 109. Arată după retragerea apei.

---

## Pasul 3. Descărcarea imaginilor radar pe calculator

1. **Adaugă la finalul codului** din editor rândurile de mai jos și apasă **Run**:
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
2. În panoul din dreapta sus, tab-ul **Tasks**, apeși **RUN** la fiecare rând, apoi încă o dată **Run** în fereastra care apare. Nu schimbi nimic acolo.
3. După 1–3 minute rândurile devin albastre, cu bifă.
4. Deschide **Google Drive** și intră în folderul `landcheck`. Descarcă cele 2 fișiere `.tif`.
5. Mută-le în `data/s1/`.

Formatul e GeoTIFF, care e cel bun.

**Rezultat verificat:** 2 fișiere de câte 57 MB. Conțin banda VV în dB, la 10 m. Apa are în jur de −18 dB sau mai puțin.

---

## Pasul 4. Apa permanentă (JRC) și relieful (DEM), din Earth Engine

**La ce folosesc:**
- **Apa permanentă (JRC)** arată unde e apă mereu, ca să nu numeri râul sau lacurile drept inundație.
- **Relieful (DEM)** arată altitudinea fiecărui punct. Apa se adună în zonele joase.

1. **Șterge doar cele 2 blocuri `Export.image.toDrive(...)` de la pasul 3.** Păstrează restul codului, mai ales `var zona = ...`.
2. Adaugă la final codul de mai jos și apasă **Run**:
```javascript
// Apa permanenta: in cate % din observatiile din 1984 incoace a fost apa (0–100)
var apa = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0).clip(zona);
Map.addLayer(apa, {min: 0, max: 100, palette: ['white', 'blue']}, 'Apa permanenta JRC');

// Relief: altitudinea in metri
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(zona)
  .select('DEM').mosaic().clip(zona);
Map.addLayer(dem, {min: 0, max: 250, palette: ['green', 'yellow', 'brown']}, 'Relief DEM');

Export.image.toDrive({image: apa, description: 'pechea_jrc_apa_permanenta',
  folder: 'landcheck', region: zona, scale: 30, crs: 'EPSG:32635', maxPixels: 1e9});
Export.image.toDrive({image: dem, description: 'pechea_dem_relief',
  folder: 'landcheck', region: zona, scale: 30, crs: 'EPSG:32635', maxPixels: 1e9});
```
3. În **Tasks**, apeși **RUN** la cele 2 rânduri noi.
4. Descarci fișierele din Drive în `data/context/`.

Mesajul galben „This asset is deprecated” de la DEM se poate ignora. Datele sunt corecte.

**Rezultat verificat:**
- `pechea_dem_relief.tif` (2,8 MB): altitudini între 5 și 168 m, cu media de 62 m. Doar ~2% pixeli goi, la margini.
- `pechea_jrc_apa_permanenta.tif` (15 KB): mic, pentru că zona e aproape toată uscat. Apa permanentă acoperă ~0,4% din zonă. Asta e versiunea JRC 1.4, cu date până în 2021. La pasul 8 o înlocuim cu versiunea nouă de pe EOCube.

---

## Pasul 5. Poze Sentinel-2 înainte și după (Earth Engine)

**Ce sunt:** poze obișnuite din satelit. Codul ia toate pozele din perioadă, scoate norii și le combină într-o singură imagine curată pentru fiecare perioadă:
- **Înainte:** 15 aug – 11 sep 2024.
- **După:** 15 sep – 5 oct 2024.

1. Șterge tot din editor, lipește codul complet de mai jos și apasă **Run**.

```javascript
// Zona Pechea
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);
Map.centerObject(zona, 11);

// ---------- Radar Sentinel-1 (orbita 109) ----------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(zona)
  .filter(ee.Filter.eq('relativeOrbitNumber_start', 109))
  .select('VV');
var inainte = s1.filterDate('2024-09-02', '2024-09-03').first().clip(zona);
var inundatie = s1.filterDate('2024-09-14', '2024-09-15').first().clip(zona);
Map.addLayer(inainte, {min: -25, max: 0}, 'Radar inainte: 2 sep 2024', false);
Map.addLayer(inundatie, {min: -25, max: 0}, 'Radar inundatie: 14 sep 2024', false);

// ---------- Apa permanenta JRC (0–100 %) ----------
var apa = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence').unmask(0).clip(zona);
Map.addLayer(apa, {min: 0, max: 100, palette: ['white', 'blue']}, 'Apa permanenta JRC', false);

// ---------- Relief DEM (metri) ----------
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(zona)
  .select('DEM').mosaic().clip(zona);
Map.addLayer(dem, {min: 0, max: 250, palette: ['green', 'yellow', 'brown']}, 'Relief DEM', false);

// ---------- Poze Sentinel-2, fara nori ----------
function faraNori(img) {
  var scl = img.select('SCL');
  var curat = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(curat).divide(10000).copyProperties(img, ['system:time_start']);
}
function pozaCurata(start, end) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zona).filterDate(start, end)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
    .map(faraNori).select(['B4', 'B3', 'B2', 'B8'])   // rosu, verde, albastru, infrarosu
    .median().clip(zona);
}
var s2Inainte = pozaCurata('2024-08-15', '2024-09-11');
var s2Dupa    = pozaCurata('2024-09-15', '2024-10-05');

var culori = {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3};
Map.addLayer(s2Inainte, culori, 'Poza inainte');
Map.addLayer(s2Dupa, culori, 'Poza dupa');

// ---------- Export (doar Sentinel-2) ----------
Export.image.toDrive({image: s2Inainte.toFloat(), description: 'pechea_s2_inainte',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9});
Export.image.toDrive({image: s2Dupa.toFloat(), description: 'pechea_s2_dupa',
  folder: 'landcheck', region: zona, scale: 10, crs: 'EPSG:32635', maxPixels: 1e9});
```

2. Uită-te pe hartă la „Poza inainte” și „Poza dupa”. Straturile de la pașii 2–4 sunt și ele acolo, dar ascunse. Le pornești din **Layers**.
3. În **Tasks**, apeși **RUN** la `pechea_s2_inainte` și `pechea_s2_dupa`.
4. Ai răbdare: exporturile Sentinel-2 durează **5–20 de minute**, pentru că se combină zeci de poze. Abia dacă trece de 30 de minute sau devine roșu e o problemă.
5. Descarci fișierele din Drive în `data/s2/`.

**Corectură față de prima versiune.** Prima variantă a codului dădea eroarea „Can't get band number 0. Image has no bands”. Cauza: funcția care scoate norii pierdea data fiecărei poze, așa că filtrul pe perioadă nu mai găsea nimic. Codul de mai sus o repară în două feluri:
- funcția folosește `.copyProperties(img, ['system:time_start'])`, deci păstrează data;
- filtrul pe dată se aplică înainte de scoaterea norilor.

**Rezultat verificat:**
- 2 fișiere, de 81 MB (înainte) și 75 MB (după).
- Fiecare are 4 benzi (B4, B3, B2, B8), 1988 × 3104 pixeli de 10 m, cu doar ~2% pixeli goi la margini.
- Valorile sunt reflectanță reală, în jur de 0,1–0,2. Earth Engine aplică deja corecția −1000 în colecția `HARMONIZED`.

---

## Pasul 6. Ploaia ANM, cu Python, de pe EOCube (fără cont)

**Ce e:** ploaia zilnică măsurată de ANM, pe o grilă de ~1 km, din 1961 încoace. Cubul întreg are **185 GB**. Scriptul citește doar septembrie 2024 peste Pechea, adică 30 de zile × 28 × 25 de celule.

### 6a. Pregătirea Python (o singură dată)

În Terminal:
```bash
python3 --version
```
De exemplu poate afișa `Python 3.14.8`. Mai departe:
```bash
cd <folderul-repo-ului>/data/cems
python3 -m venv .venv
source .venv/bin/activate
pip install xarray zarr aiohttp requests fsspec pandas
```
Mediul Python (`.venv`) a ajuns în folderul `data/cems`. Funcționează la fel de oriunde.

**Când redeschizi Terminalul**, rulezi mereu întâi:
```bash
cd <folderul-repo-ului>/data
source cems/.venv/bin/activate
```
La început de rând trebuie să apară `(.venv)`.

### 6b. Scriptul de ploaie

Din folderul `date`, creezi scriptul lipind tot blocul deodată:
```bash
cat > anm_ploaie.py << 'EOF'
import os
import xarray as xr

URL = "https://storage.svc.uvt-01.eocube.ro/meteo/cube/open-v1/"
VEST, SUD, EST, NORD = 27.6159, 45.4607, 27.8670, 45.7384

ds = xr.open_zarr(URL, consolidated=True)
print(ds)  # arata ce variabile si axe are cubul

# gaseste numele axelor (pot fi lon/lat sau x/y)
xn = next(n for n in ("lon", "longitude", "x") if n in ds.dims)
yn = next(n for n in ("lat", "latitude", "y") if n in ds.dims)
y = ds[yn]
ysl = slice(SUD, NORD) if float(y[0]) < float(y[-1]) else slice(NORD, SUD)

p = ds["precipitation"].sel(time=slice("2024-09-01", "2024-09-30"))
p = p.sel({xn: slice(VEST, EST), yn: ysl}).load()
print("Celule in zona:", p.sizes)

zilnic = p.mean([xn, yn]).to_series().round(1)
os.makedirs("anm", exist_ok=True)
zilnic.to_csv("anm/ploaie_medie_pechea_sep2024.csv", header=["mm"])
p.to_dataframe().reset_index().to_csv("anm/ploaie_grid_pechea_sep2024.csv", index=False)

print("\nPloaia medie pe zona Pechea (mm/zi):")
print(zilnic.to_string())
print("\nTotal 10-16 sep:", round(zilnic["2024-09-10":"2024-09-16"].sum(), 1), "mm")
EOF
```
Apoi îl rulezi:
```bash
python3 anm_ploaie.py
```

**Ce vezi:** descrierea cubului (185 GB, axele `x` și `y`, din 1961 până în 2050), apoi `Celule in zona: time 30, y 28, x 25` și ploaia pe fiecare zi.

**Rezultat verificat** (media pe zona Pechea):

| Zi | mm |
|---|---|
| 6–7 sep | 4,6 și 8,1 |
| **12 sep** | **17,4** |
| 13 sep | 0,5 |
| **14 sep** | **57,4** |
| 15 sep | 1,7 |
| **16 sep** | **31,2** |
| 18 sep | 4,8 |
| 30 sep | 15,8 |
| **Total 10–16 sep** | **108,2 mm** |

Fișiere create:
- `data/anm/ploaie_medie_pechea_sep2024.csv`, cu media pe zi;
- `data/anm/ploaie_grid_pechea_sep2024.csv`, cu fiecare celulă.

Atenție la două lucruri:
- La ANM o „zi” de ploaie se măsoară de obicei între 06:00 și 06:00 a doua zi. Valoarea de pe 14 sep poate include deci și noaptea de 13 spre 14 sep.
- Zilele încă nescrise în cub apar ca 0, nu ca lipsă. Pentru perioade recente, verifică întâi `last_precipitation_time`.

---

## Pasul 7. Mișcarea terenului, EGMS (cont EU Login, gratuit)

**Ce e:** cât se ridică sau coboară terenul (mm/an), măsurat din radar între 2020 și 2025.

1. Intră pe **egms.land.copernicus.eu**.
2. **Login:** nu e un buton scris, ci o **iconiță cu lacăt** 🔒 în bara de unelte, cu textul „Sign in with EU Login”. Direct: https://egms.land.copernicus.eu/login. Dacă nu ai cont, apasă **Create an account** și confirmă din email.
3. Deschide lista de straturi (iconița ☰ sau cea de straturi), apoi **ORTHO (Level 3)**, apoi pornește **Vertical 2020-2025**.
4. Mergi la Pechea. Coordonatele afișate jos, de exemplu `WGS84 45.6228 N 27.8436 E`, te ajută să știi unde ești.
5. **Ce vezi:** puncte mici pe fundal negru, câte unul la ~100 m. Aproape toate sunt verzi, adică teren stabil. Ca să vezi diferențele mici, schimbă scala din panoul „Vertical” la −5 … 5.
6. Selectează o zonă în jurul Pechea. Se deschide o fereastră cu un grafic, de exemplu „Average of 559 points”.
7. Salvează datele (nu există buton de download, se face prin copiere):
   - din meniul din stânga sus al ferestrei alege seria, de exemplu „1. Vertical: Average of 559 points”;
   - apasă **View Data**;
   - dă click în tabel, apoi **Cmd+A** și **Cmd+C**;
   - în Terminal, din folderul `date`, rulează:
   ```bash
   mkdir -p egms && pbpaste > egms/egms_pechea_vertical.txt && head -3 egms/egms_pechea_vertical.txt
   ```
   Pe al doilea rând trebuie să scrie `Dataset Vertical`.
   - Repetă pentru East/West, cu `pbpaste > egms/egms_pechea_east_west.txt`.
8. **Generate SVG**, în aceeași fereastră, salvează graficul ca imagine. Îl muți în `data/egms/`.

**Rezultat verificat:**
- **Media celor 508 puncte, vertical:** `egms_pechea_medie_508_vertical.txt`, 303 măsurători între 9 dec 2020 și 25 nov 2025. `mean_velocity` din antet: **−0,70 mm/an**. Panta recalculată din date: −0,69 mm/an. Terenul s-a lăsat în total cam 3,3 mm în 5 ani. E **stabil**, sub pragurile din proiect: −2 mm/an pentru „mediu” și −5 mm/an pentru „mare”.
- **Media celor 559 de puncte, est-vest:** `egms_pechea_east_west.txt`, `mean_velocity` 0,03 mm/an, deci nicio mișcare laterală.
- `egms_pechea_vertical.txt`: **un singur punct** (ID `40WX2NMaTf`), cu `mean_velocity` +0,5 mm/an. Un alt punct, `40WWxghLHa`, are −0,1 mm/an. Ambele sunt stabile.
- Numărul de puncte din medie diferă (559 și 508) pentru că depinde de zona selectată cu mouse-ul. Rezultatul e același: stabil.

Arhiva de produse (iconița cu cilindru) a rămas goală. Pentru Pechea nu e nevoie de ea, pentru că media e suficientă.

Concluzie pentru aplicație: „Mișcarea terenului la Pechea: stabil, aproximativ −0,7 mm/an (media a ~500 de puncte EGMS, 2020–2025).”

---

## Pasul 8. Apa permanentă nouă (JRC v1.5), de pe EOCube

**De ce:** e aceeași hartă de apă permanentă de la pasul 4, dar versiunea mai nouă, cu date **până în 2024**. Cea din Earth Engine are date doar până în 2021. În plus, vine de pe EOCube, platforma echipei.

1. Din folderul `date`, cu `(.venv)` activ:
```bash
pip install pystac-client odc-stac rioxarray
```
2. Creează scriptul (lipești tot blocul):
```bash
cat > eocube_jrc.py << 'EOF'
import rioxarray
from pystac_client import Client
import odc.stac
from shapely.geometry import box

zona = box(27.6159, 45.4607, 27.8670, 45.7384)
cat = Client.open("https://stac.eocube.ro")
items = list(cat.search(collections=["jrc-gsw-v1-5-occurrence"], intersects=zona).items())

# fisierele sunt pe stocarea EOCube: le citim prin HTTPS, ca la ANM
for it in items:
    for a in it.assets.values():
        if a.href.startswith("s3://"):
            a.href = a.href.replace("s3://", "https://storage.svc.uvt-01.eocube.ro/")
print("Fisier:", items[0].assets["occurrence"].href)

data = odc.stac.load(items, geopolygon=zona, crs="EPSG:32635", resolution=30, bands=["occurrence"])
data["occurrence"].isel(time=0).rio.to_raster("context/pechea_jrc_occurrence_v1_5_eocube.tif")
print("Salvat: context/pechea_jrc_occurrence_v1_5_eocube.tif")
EOF
```
3. Rulează:
```bash
python3 eocube_jrc.py
```

**Ce vezi:** linia `Fisier: https://storage.svc.uvt-01.eocube.ro/jrc-gsw-v1-5/...occurrence_20E_50N_v1_5_2024.tif`, apoi `Salvat: ...`.

**Corecturi față de prima versiune** (au apărut ca erori pe parcurs):
1. Eroarea `InvalidCredentials: No valid AWS credentials found`. În catalog, fișierele EOCube au adrese `s3://...`, care cer cont. Scriptul le transformă în adrese `https://storage.svc.uvt-01.eocube.ro/...`, care merg fără cont.
2. Eroarea `'DataArray' object has no attribute 'rio'`. Lipsea `import rioxarray` la începutul scriptului.

**Rezultat verificat:**
- `context/pechea_jrc_occurrence_v1_5_eocube.tif` (673 KB): aceeași grilă ca la pasul 4, 664 × 1035 pixeli de 30 m.
- Valorile sunt între 0 și 95%. Apa permanentă (peste 50% din timp) acoperă **0,44%** din zonă, față de 0,40% în versiunea veche.

De acum se folosește acest fișier. Cel vechi (`pechea_jrc_apa_permanenta.tif`) rămâne doar ca rezervă.

Același script merge pentru orice colecție EOCube. Schimbi doar numele colecției și al benzii, de exemplu `jrc-gsw-v1-5-monthlyhistory`, care are apa lună cu lună, inclusiv septembrie 2024.

---

## Pasul 9. Folosirea terenului în timp (landuse): NDVI de vară, 2018–2025

**Ce e:** NDVI e un număr de la −1 la 1 care arată cât de verde e vegetația. Aproape de 1 înseamnă vegetație deasă, aproape de 0 teren gol, drum sau construcții. Un câmp cultivat își schimbă NDVI-ul de la an la an și în cursul anului, o pădure rămâne verde, iar terenul construit rămâne mereu fără verde. Din NDVI se poate deduce cum a fost folosit terenul. Aici facem câte o imagine pe an, doar pentru vară (iunie–august), din 2018 încoace. Înainte de 2018, Sentinel-2 are puține imagini corectate peste Europa.

1. În Earth Engine șterge tot din editor, lipește codul de mai jos și apasă **Run**.

```javascript
// Zona Pechea
var zona = ee.Geometry.Rectangle([27.6159, 45.4607, 27.8670, 45.7384]);
Map.centerObject(zona, 11);

function faraNori(img) {
  var scl = img.select('SCL');
  var curat = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return img.updateMask(curat).copyProperties(img, ['system:time_start']);
}

// NDVI mediu pe vara (iunie–august) pentru un an
function ndviVara(an) {
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(zona)
    .filterDate(an + '-06-01', an + '-08-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 60))
    .map(faraNori);
  print(ee.String('Poze folosite in ' + an + ': ').cat(ee.Number(col.size()).format()));
  return col.map(function(img) { return img.normalizedDifference(['B8', 'B4']); })
    .median().clip(zona).rename('NDVI_' + an);
}

var ani = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];
var ndviAni = ee.Image.cat(ani.map(ndviVara));

var paleta = {min: 0, max: 0.9, palette: ['brown', 'yellow', 'green', 'darkgreen']};
Map.addLayer(ndviAni.select('NDVI_2018'), paleta, 'NDVI vara 2018');
Map.addLayer(ndviAni.select('NDVI_2024'), paleta, 'NDVI vara 2024');

Export.image.toDrive({image: ndviAni.toFloat(), description: 'pechea_ndvi_vara_2018_2025',
  folder: 'landcheck', region: zona, scale: 20, crs: 'EPSG:32635', maxPixels: 1e9});
```

2. **Ce vezi:** în panoul **Console** apar numerele de poze folosite pentru fiecare an. Pe hartă, din **Layers**, pornești „NDVI vara 2018” și „NDVI vara 2024”. Verdele închis e vegetație deasă, galbenul și maroul sunt teren gol sau recoltat.
3. În **Tasks** apeși **RUN** la `pechea_ndvi_vara_2018_2025`, apoi **Run** în fereastra care apare. Descarci din Google Drive un singur fișier `.tif`, nu un zip, și îl pui în `data/landuse/`.

**Despre avertismentul galben de la `print`.** Prima versiune avea `print('Poze folosite in ' + an + ':', col.size())` și editorul afișa „print() called with too many arguments”. E doar un avertisment, nu o eroare, iar codul rula oricum. Versiunea de mai sus nu mai are avertismentul, dar n-am testat-o separat în Earth Engine.

**Rezultat verificat:**
- `landuse/pechea_ndvi_vara_2018_2025.tif` (52 MB): 8 benzi (`NDVI_2018` … `NDVI_2025`), 995 × 1553 pixeli de 20 m, în `EPSG:32635`. Doar ~2% pixeli goi, la margini.
- Mediana NDVI pe toată zona, pe ani: 2018: 0,56, 2019: 0,55, 2020: 0,30, 2021: 0,65, 2022: 0,33, 2023: 0,43, 2024: 0,24, 2025: 0,39. Valorile sunt între −0,5 și 0,93.

**Atenție la interpretare:** diferențele mari de la un an la altul (de exemplu 2021 față de 2024) vin probabil în mare parte din vreme (secetă, caniculă) și din ce s-a cultivat în acel an, dar asta e o presupunere, nu am verificat-o. Un NDVI mic într-un singur an nu înseamnă că terenul și-a schimbat folosința. Pentru asta trebuie comparate mai mulți ani și mai multe luni, iar numărul de poze din Console arată cât de solidă e fiecare imagine.

---

## Ce ai la final

```
data/                                      (~340 MB, nu intră în git)
├── cems/       3 ZIP CEMS: inundația pe 14, 15 și 17 sep 2024   (+ .venv, mediul Python)
├── s1/         radar 2 sep și 14 sep 2024 (VV, dB, 10 m)
├── s2/         poze înainte și după (B4, B3, B2, B8, reflectanță, 10 m)
├── context/    JRC v1.5 EOCube (de folosit), JRC v1.4 (rezervă), DEM 30 m
├── anm/        ploaia zilnică, septembrie 2024 (medie și grilă)
├── egms/       mișcarea terenului 2020–2025 (medie 508 puncte vertical, medie 559 puncte est-vest, un punct, grafice SVG)
├── landuse/    NDVI de vară pe ani, 2018–2025 (un fișier cu 8 benzi, 20 m)
├── anm_ploaie.py
└── eocube_jrc.py
```

**Checksum-uri (SHA-256)** pentru fișierele mari:
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
Checksum-urile pentru fișierele Earth Engine nu vor fi identice dacă le exporți din nou. Conținutul e același, dar fișierul generat diferă puțin.

## Ce nu am luat și de ce

| Date | De ce nu |
|---|---|
| DEM de pe EOCube (`copernicus-dem-30`) | E exact același DEM pe care îl avem deja din Earth Engine |
| JRC `extent` și `recurrence` de pe EOCube | Informație mai săracă sau care nu ne trebuie acum |
| JRC `monthlyhistory` | Opțional. Se poate lua cu scriptul de la pasul 8 |
| Sentinel-1 de pe EOCube | EOCube nu are imagini radar pentru 10–20 sep 2024 |
| Date direct de pe dataspace.copernicus.eu | Aceleași imagini Copernicus le-am luat mai simplu prin Earth Engine |
| Istoric de landuse înainte de 2018 | Sentinel-2 corectat (L2A) are puține imagini peste Europa înainte de 2018 |
| Fiecare punct EGMS separat | Media pe zonă e suficientă pentru Pechea. Arhiva de produse EGMS a rămas goală |
| Model ML | Avem un singur eveniment. Un model are nevoie de multe inundații din multe zone ca să învețe ceva corect |
