# web/data – veri sözleşmesi

Şu anki dosyalar **sahte** (`scripts/make_dummies.py`, her kayıtta `"dummy": true`).
Gerçekleri E3 (layers, grid) ve E7 (regions, stories, poi) ile aynı adlarla gelecek; alanlar değişmeyecek.
Koordinatlar derece, doğu pozitif, boylam -180..180.

| Dosya | Biçim |
| --- | --- |
| `regions.json` | Dizi. `{id, name, lat, lon, elevation_m, science_value (1-5), summary, hazards[], missions[], history[{date, event, source}], sol, photos[{url, sol, camera, caption}]}` |
| `poi.geojson` | FeatureCollection, Point. `properties: {id, name, type: habitat/science/hazard/history, region_id?, story_ids?, note?}` |
| `stories.json` | Dizi. `{id: apollo14/opportunity/spirit, title, date, body, location_text, lesson, layer, source}` |
| `layers.json` | Dizi. `{id, name, file: "layers/x.png", bbox: [batı, güney, doğu, kuzey], default_opacity, legend[{color, label}], source}` |
| `grid.json` | `{width: 256, height: 256, bounds: {west, south, east, north}, cell_size_m, elev[], cost[], blocked[]}` düz diziler, satır 0 = kuzey, `indeks = satır*width + sütun`. `cost` = dk/hücre. |
| `astronauts.json` | Dizi (Ayşe, Ali). `{id, name, mass_kg, suit, o2_min, o2_capacity_min, battery_pct, water_pct, heart_rate, load_kg, radiation_msv, role, position{lat, lon}}` |
| `conditions.json` | Dizi, Sol bazında. `{sol, temp_min_c, temp_max_c, pressure_pa, wind_ms, dust_tau, sunrise_lmst, sunset_lmst}` |
| `photos/` | Fotoğraflar (şimdilik tek yer tutucu). |
