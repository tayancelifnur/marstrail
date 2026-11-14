# MarsTrail – Çalışma günlüğü

Her kartın sonunda: kart, saat, ne yapıldı, değişen dosyalar, nasıl çalıştırılır, varsayımlar.

## E1 · Repo ve sahte veri · Cmt 14 Kas 2026, bitiş 15:23 (commit 3145252)

- **Ne yapıldı:** Klasör yapısı, `.gitignore`, Python 3.12 venv + paketler; Gözde için veri sözleşmesine uygun sahte `web/data/` dosyaları.
- **Dosyalar:** `.gitignore`, `requirements.txt`, `scripts/make_dummies.py`, `web/data/*` (regions, poi, stories, layers + 5 PNG, grid, astronauts, conditions, photos/placeholder.jpg, README.md), `ml/.gitkeep`.
- **Çalıştır:** `py -3.12 -m venv venv` → `venv\Scripts\python -m pip install -r requirements.txt` → `venv\Scripts\python scripts\make_dummies.py`
- **Varsayımlar:** Çalışma alanı 77.36–77.51°D, 18.38–18.52°K; grid 256×256 (~32 m hücre). Arazi sentetik (taban −2600 m, delta tümseği, delta yamacı, 3 krater, Séítah benzeri sırtlar → %0,8 geçilmez, rota testi için). Maliyet PLAN.md §5 Tobler formülü (yük 0 kg). Nokta koordinatları ve Sol'ler yaklaşık; her kayıtta `"dummy": true`.
- **GPU (sonradan, E2 sırasında):** torch 2.11.0+cu128 kuruldu (`pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`); RTX 5090 Laptop (sm_120) görünüyor, ultralytics CUDA:0 ile çalışıyor. requirements.txt'teki düz `torch` CPU sürümünü kurar, GPU için bu komut ayrıca çalıştırılmalı.
