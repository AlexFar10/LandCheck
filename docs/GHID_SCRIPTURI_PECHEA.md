# Ghid: de la datele descărcate la modulele LandCheck (Pechea)

Acest ghid explică ce am făcut după descărcarea datelor pentru Pechea (vezi `GHID_DESCARCARE_DATE_PECHEA.md`): cum am transformat datele brute în date curate, ce face fiecare fișier de cod, cum se rulează și de ce am ales fiecare regulă. Nu presupune că știi programare. Fiecare fișier are o secțiune cu intrare, ieșire și reguli.

## 1. Imaginea de ansamblu

Aplicația primește o **parcelă** (un teren desenat pe hartă) și răspunde la patru întrebări, câte un „modul” pentru fiecare:

| Întrebare | Modul | Date folosite |
|---|---|---|
| A fost parcela sub apă? | `flood_history` | Inundația CEMS (13–17 sept 2024), plus ploaie, relief și apă permanentă ca context |
| Cum a fost vegetația în ani? | `land_use` | NDVI de vară 2018–2025 |
| Se mișcă terenul? | `ground_stability` | Puncte radar EGMS 2020–2025 |

Fluxul are doi pași mari:

```
date brute (data/, în afara git)
   │   scripturi „ingest”: verifică, curăță, taie zona, scriu fișiere mici
   ▼
dataset curat (datasets/pilot-pechea/, în git)
   │   module: citesc datasetul și răspund pentru o parcelă
   ▼
rezultat în formatul comun (ModuleResult): nivel, valoare, încredere, text, surse
```

### Regulile pe care le respectă tot codul (din PRD, secțiunea 8)

1. **Lipsa datelor înseamnă „Unknown”, niciodată „risc mic”.** Dacă nu avem nimic despre parcelă, spunem „No coverage”.
2. **Nu inventăm clase de risc.** High, Medium sau Low apar doar dacă avem o metodă documentată. Altfel arătăm măsurătoarea.
3. **Coordonate:** se stochează în WGS84 (lon, lat). Măsurătorile (suprafețe, distanțe) se fac în metri, în UTM (EPSG:32635 pentru Pechea).
4. **Datele brute nu intră în git.** Intră doar datele procesate și mici.
5. **Rezultatul e determinist:** aceeași intrare dă aceleași fișiere, octet cu octet.
6. **Checksum greșit oprește tot.** Scriptul nu continuă niciodată cu date neverificate.

## 2. Ce am făcut, pas cu pas

### Pasul 0. Pregătirea
- Ramură nouă din `dev`: `feature/cems-ingest`. Regula proiectului: o ramură pentru fiecare lucru, PR către `dev`, `dev` și `main` sunt protejate.
- Mediul Python (`.venv`) a fost refăcut la rădăcina proiectului:
  ```
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev,ingest,landuse]"
  ```
- În `pyproject.toml`: extra nou `ingest = ["geopandas"]`, iar `landuse` include acum și `rasterio`.

### Pasul 1. Inundația CEMS → `datasets/pilot-pechea/v1` (`ingest/cems.py`)
Cele trei arhive CEMS au fost verificate (sumă de control SHA-256, fixată în PRD), citite, curățate și scrise în formatul pe care îl cere API-ul. Rezultat: 108, 131 și 237 de poligoane, cu 1, 2 și 63 de geometrii reparate. Suprafețele (1078,6, 866,7 și 427,4 ha) se potrivesc cu PRD.

### Pasul 2. Modulul de inundație (`modules/flood.py`)
Parcela se compară cu cele trei straturi. Există trei rezultate posibile: suprapunere (High), în zona pozei dar fără poligon (Unknown, „nu înseamnă că e sigur”) sau în afara pozei (No coverage).

### Pasul 3. Folosirea terenului (`modules/landuse.py`)
Citește NDVI-ul de vară pe fiecare an din `pechea_ndvi_vara_2018_2025.tif`. Nu clasifică terenul, fiindcă o valoare pe vară nu ajunge pentru asta.

### Pasul 4. Mișcarea terenului: date și scripturi
- Mai întâi am încercat media pe zonă, copiată manual din EGMS Explorer. Nu spune nimic despre o parcelă anume.
- Soluția: descărcarea oficială a „dalelor” EGMS (butonul Download din Explorer). S-au descărcat 4 dale de 100 km (două pentru fiecare componentă, vertical și est-vest), în total ~450 MB.
- `ingest/egms.py` taie din ele doar zona pilot (14.608 puncte) și scrie un CSV mic.
- `modules/ground.py` caută punctele din jurul parcelei și dă viteza mediană.
- **Verificare:** media celor mai apropiate 508 puncte din fișierele descărcate iese −0,702 mm/an, față de −0,698 în Explorer (diferență 0,004). Pe est-vest: 0,043 față de 0,031. Datele sunt consistente.

### Pasul 5. Context pentru inundații (`modules/flood_context.py`)
Ploaie, relief și apă permanentă adăugate lângă rezultatul de inundație. Nu schimbă niciodată nivelul.

### Pasul 6. Teste și commit-uri
Câte un set de teste pentru fiecare fișier. La final: 78 de teste trec. Commit-uri locale pe `feature/cems-ingest`:

| Commit | Conținut |
|---|---|
| `d2bd40c` | ingest CEMS și datasetul `pilot-pechea/v1` |
| `3fa09d7` | `flood_history` |
| `4275b03` | `land_use` |
| `e755f1e` | ingest EGMS și `ground_stability` |
| `e9ceaed` | context pentru inundații (ploaie, relief, JRC) |

## 3. Ce face fiecare fișier

### 3.1 `landcheck/ingest/cems.py`

**Rol:** transformă cele trei arhive CEMS în datasetul pe care îl citește API-ul.

**Intrare:** `data/cems/EMSR758_AOI03_*.zip` (3 fișiere).
**Ieșire:** `datasets/pilot-pechea/v1/` cu `manifest.json`, `coverage.geojson` și `layers/<layer_id>.geojson` (3 straturi), plus raportul `datasets/pilot-pechea/v1.ingest.json`.

**Pașii, în ordine:**
1. Verifică mărimea și suma de control a fiecărei arhive față de valorile din PRD (7.3). Dacă una e greșită, oprește tot, înainte să scrie ceva.
2. Dezarhivează și citește trei straturi: `observedEventA` (poligoanele inundate), `areaOfInterestA` (zona cerută) și `imageFootprintA` (cât a văzut satelitul).
3. Repară poligoanele invalide (`make_valid`), păstrează doar suprafețe, și înregistrează câte au fost reparate și cum s-a schimbat suprafața.
4. Calculează suprafața în EPSG:32635.
5. Acoperirea fiecărui strat = zona cerută ∩ zona văzută de satelit.
6. Rotunjește coordonatele la ~0,1 m, orientează inelele conform RFC 7946 și dă fiecărui poligon un **ID calculat din forma lui** (`<layer_id>-<12 caractere hash>`). Aceeași formă dă mereu același ID.
7. Scrie fișierele, apoi hash-ul fiecărui fișier în raport.

**Reguli:**
- Refuză să scrie peste un folder existent. Versiunile de dataset sunt imuabile; o schimbare înseamnă o versiune nouă.
- Numărul de poligoane se verifică față de PRD (108, 131, 237).
- Raportul stă în afara folderului `v1`, pentru că API-ul refuză fișierele în plus din dataset.

**Rulare:**
```
python -m landcheck.ingest.cems --raw data/cems --out datasets/pilot-pechea/v1
```

### 3.2 `landcheck/modules/flood.py`

**Rol:** răspunde „a fost parcela mapată ca inundată?”. Returnează două rezultate: `flood_history` și `flood_susceptibility` (acesta din urmă spune doar „Not assessed”, modelul fiind în afara MVP-ului).

**Intrare:** o parcelă (`Parcel`). **Citește:** `datasets/pilot-pechea/v1` (sau folderul din variabila `LANDCHECK_DATASET_DIR`).

**Cum decide, pentru fiecare strat:**
- Măsoară în metri, în UTM-ul parcelei: cât din parcelă a văzut satelitul și cât a fost mapat ca inundat.
- Suprapunere ≥ 1 m² → `observed`. Acoperit dar fără suprapunere → `not_observed`. În afara pozei → `no_coverage`.

**Rezultatul final:**
- Cel puțin un strat cu inundație: nivel **High**, valoarea = cel mai mare procent din parcelă, încredere High dacă parcela e acoperită complet de poze, altfel Medium. Textul spune data, senzorul și că e o singură imagine, nu vârful inundației.
- Parcelă acoperită, dar fără poligon: **Unknown** și textul „nu înseamnă că terenul e sigur”.
- Nicio imagine nu acoperă parcela sau datasetul lipsește: **Unknown**, „No coverage”.

### 3.3 `landcheck/modules/flood_context.py`

**Rol:** adaugă fapte lângă rezultatul de inundație, fără să schimbe nivelul. Orice parte lipsă sau în afara datelor se sare, fără eroare.

**Date (în `datasets/pilot-pechea/context/`):**

| Parte | Fișier | Ce spune |
|---|---|---|
| Ploaie | `ploaie_grid_pechea_sep2024.csv` | Suma pe 5 zile până la data imaginii, ziua cea mai ploioasă, din celula de grilă (0,01°) cea mai apropiată de parcelă |
| Relief | `pechea_dem_relief.tif` | Altitudine, pantă și cât din terenul din 2 km e mai jos decât parcela |
| Apă permanentă | `pechea_jrc_occurrence_v1_5_eocube.tif` | Dacă pixelii parcelei au apă ≥ 50% din timp |

**Cum apare în rezultat:** totul intră în `details["context"]`. Doar ploaia și apa permanentă adaugă câte o frază în text, și doar când parcela a fost mapată ca inundată. Exemplu real: „Rain in the 5 days up to 2024-09-14: 81.9 mm (most on 2024-09-14, 64.4 mm).”

**Atenție:** DEM și JRC sunt la 30 m, deci pentru parcele mici sunt aproximative. Pragul de 50% e luat din `config/thresholds.yaml` (valoare provizorie).

### 3.4 `landcheck/modules/landuse.py`

**Rol:** arată cum a variat vegetația de vară a parcelei între 2018 și 2025.

**Intrare:** parcela. **Citește:** `data/landuse/pechea_ndvi_vara_2018_2025.tif` (sau `LANDCHECK_NDVI_PATH`). Fișierul nu e în git, fiind mare (53 MB).

**Cum lucrează:**
- Pentru fiecare an ia mediana NDVI a pixelilor (20 m) din parcelă. Pixelii goi rămân goi, fără completare.
- Parcelă mai mică decât un pixel: ia pixelul pe care îl atinge.
- Parcelă doar parțial în zonă: spune ce procent e înăuntru.

**Rezultat:** nivel mereu **Unknown**. Textul dă intervalul („între 0,17 și 0,76, 2018–2025”) și precizează că se măsoară doar vara, deci nu arată cum a fost folosit terenul. Dacă NDVI e sub 0,2 în toți anii, adaugă „vegetație rară”.

**De ce nu clasifică:** pentru a deosebi un câmp de o pădure e nevoie de ciclul de creștere pe tot anul. Un an slab (de exemplu 2024) poate fi doar secetă. Clasificarea se poate adăuga când avem NDVI și pentru primăvară și toamnă.

### 3.5 `landcheck/ingest/egms.py`

**Rol:** taie din dalele EGMS mari doar zona pilot și le face utilizabile.

**Intrare:** folderele `data/egms/EGMS_L3_*` (vertical `U` și est-vest `E`, fiecare cu CSV). Fiecare rând din CSV = un punct radar, cu coordonate în EPSG:3035, viteza medie în mm/an și seria de timp.
**Ieșire:** `datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv` (14.608 puncte, fără seria de timp) și raportul `.ingest.json`.

**Pașii:**
1. Găsește dalele și cere ambele componente pentru fiecare dală. Dacă una lipsește, oprește.
2. Zona = acoperirea CEMS + 5 km, ca dreptunghi în EPSG:3035.
3. Citește fiecare CSV rând cu rând (fișierele au ~135 MB), păstrează doar punctele din zonă.
4. Lipește vertical și est-vest după ID-ul punctului și trece coordonatele în lat/lon.
5. Scrie CSV-ul sortat după ID, deci determinist.
6. În raport: suma de control a celor 4 CSV-uri, numărul de puncte și **verificarea mediilor tale** din Explorer (media celor mai apropiate K puncte față de media publicată).

**Rulare:**
```
python -m landcheck.ingest.egms --raw data/egms \
  --coverage datasets/pilot-pechea/v1/coverage.geojson \
  --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv \
  --average data/egms/egms_pechea_medie_508_vertical.txt \
  --average data/egms/egms_pechea_east_west.txt
```

### 3.6 `landcheck/modules/ground.py`

**Rol:** pentru o parcelă, spune cum se mișcă terenul (mm/an, negativ = se scufundă).

**Cum lucrează:**
1. Citește CSV-ul mic de puncte (o dată, apoi îl ține în memorie).
2. Ia punctele din parcelă plus zona tampon (500 m), în EPSG:3035.
3. Niciun punct → **No coverage** (niciodată „stabil”). Punctele radar apar doar pe clădiri, drumuri și teren gol; câmpurile au rar puncte.
4. Altfel calculează mediana verticală, intervalul dintre cuartile (cât se contrazic punctele), numărul de puncte, mediana est-vest și accelerația.

**Încrederea:**
- High: cel puțin 10 puncte și cuartilele la mai puțin de 1 mm/an una de alta.
- Medium: cel puțin 3 puncte (pragul din `thresholds.yaml`) și diferență sub 2 mm/an.
- Low: altfel. Dacă vecinii se contrazic, textul adaugă „tratează cu prudență”.

**Nivelul rămâne Unknown.** Pragurile din `thresholds.yaml` (−2 și −5 mm/an) sunt provizorii și nu au o metodă documentată. Valoarea măsurată se afișează. Dacă echipa adoptă pragurile, se schimbă într-un singur loc.

### 3.7 Teste (`tests/`)

| Fișier | Ce verifică |
|---|---|
| `test_ingest_cems.py` | Poligon invalid reparat; ID stabil; checksum greșit oprește; datasetul se încarcă în API; două rulări dau fișiere identice; refuză suprascrierea; nimic scris dacă o arhivă e alterată |
| `test_flood.py` | Parcelă în zonă inundată = High; parțial în zonă = procent; acoperită fără poligon = Unknown; în afara pozei = No coverage; dataset lipsă; un test pe datele reale |
| `test_flood_context.py` | Ploaie (sumă, ziua maximă, celula apropiată), relief (pantă, poziție), JRC, fișiere lipsă, context în rezultat |
| `test_landuse.py` | Interval NDVI, vegetație rară, parcelă sub un pixel, parțial în afară, în afară, fișier lipsă, test pe raster real |
| `test_ingest_egms.py` | Tăierea la zonă, lipirea vertical + est-vest, verificarea mediilor, dală incompletă, refuz de suprascriere |
| `test_ground.py` | Încredere mare, vecini care se contrazic, fără puncte = No coverage, fișier lipsă, parcelă îndepărtată |

Testele care au nevoie de fișiere mari din afara git (arhivele CEMS, rasterul NDVI) **se sar singure** când acestea lipsesc. Restul folosesc date mici făcute pe loc. Rulare: `pytest` (78 de teste).

### 3.8 Unde stă fiecare lucru

```
data/                      date brute, în afara git (CEMS, EGMS, NDVI, s1, s2 etc.)
datasets/pilot-pechea/
├── v1/                    inundația CEMS (citită de API): manifest, coverage, 3 straturi
├── v1.ingest.json         raportul ingest-ului CEMS (sume de control, reparări)
├── context/               ploaie, relief, JRC (+ README cu sursele)
└── ground/                punctele EGMS din zonă (+ raportul ingest-ului)
landcheck/ingest/          scripturile care fac datasetul (cems.py, egms.py)
landcheck/modules/         modulele care răspund pentru o parcelă
tests/                     testele
```

## 4. Decizii și puncte deschise

| Subiect | Ce am ales | De ce |
|---|---|---|
| Nivelul la `land_use` și `ground_stability` | Unknown | Nu avem o metodă documentată (PRD 8.1) |
| Nivelul la inundație | High doar la suprapunere cu un poligon mapat | E un fapt observat; absența poligonului nu înseamnă risc mic |
| Context (ploaie, relief, JRC) | Doar fapte, nu schimbă nivelul | Evităm un scor artificial combinat |
| JRC | Inclus, deși CEMS separă deja apa permanentă | E simplu de adăugat și util ca avertisment |
| Raportul de ingest | Fișier separat, în afara datasetului | API-ul refuză fișiere în plus |
| Date în git | Datasetul curat și contextul mic (~6 MB). Rasterele cu `git add -f` | `.gitignore` ignoră `*.tif` |
| Termeni de folosire | Datele sunt considerate deschise | PRD cere confirmare (D-03), de menționat în PR |

**De aliniat cu partenerul:** manifestul din PRD 7.4 are câmpuri pe care încărcătorul strict din API nu le acceptă. Tot așa, atribuirea sursei și termenii EGMS și CEMS pentru reutilizare comercială.

## 5. Ce nu e făcut

- Clasificarea reală a folosirii terenului (nevoie de NDVI pe tot anul).
- Clase de risc pentru mișcarea terenului (nevoie de o metodă documentată).
- Harta hazardului ANAR (nu există sursă citibilă automat).
- Corecția offset-ului Sentinel-2 din `core/s2.py` (necesară doar dacă se folosește S2 din EOCube).
- Contextul de ploaie e doar pentru septembrie 2024 (alte evenimente cer alte date).

## 6. Rulare completă, de la zero

```
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ingest,landuse]"
python -m landcheck.ingest.cems --raw data/cems --out datasets/pilot-pechea/v1
python -m landcheck.ingest.egms --raw data/egms --coverage datasets/pilot-pechea/v1/coverage.geojson \
  --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv
pytest
```

Dacă folderele `datasets/pilot-pechea/v1` sau fișierul EGMS există deja, scripturile refuză să scrie peste ele. Șterge-le intenționat, sau folosește un nume nou.
