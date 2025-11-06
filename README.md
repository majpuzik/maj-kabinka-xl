# 🎨 Virtual Fitting Room - Complete XL Edition

AI-Powered Virtual Try-On System s kompletním GUI, databází, webcam support a více featury.

## ✨ Hlavní Features

1. **📸 Webcam Support** - Foťte osobu i oblečení přímo z webkamery
2. **🔗 URL Import** - Načtěte oblečení z URL s automatickým odstraněním pozadí
3. **💾 Databáze** - Kompletní historie všech generování s metadaty
4. **⭐ Rating System** - Hodnoťte výsledky 1-5 hvězdičkami (editovatelné)
5. **💰 Generování Varianty** - Local/Paid/Cloud Free/Premium s cenami a časováním
6. **⏱️ Time Tracking** - Automatické měření času generování
7. **🚫 Auto-Blacklist** - Varianty trvající >3 min jsou automaticky zakázány
8. **🖨️ Print View** - Tiskněte výsledky s vstupy, výstupy a metadaty
9. **📊 Sidebar Historie** - Rychlý přístup ke všem předchozím generováním

## 🚀 Rychlý Start

### 1. Backend (Port 8000)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (Port 5001)

```bash
cd frontend-flask
source ../backend/venv/bin/activate
pip install flask rembg
python app_complete.py
```

### 3. Otevřít v prohlížeči

- **Frontend GUI**: http://localhost:5001
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 Struktura Projektu

```
maj-kabinka-xl/
├── backend/
│   ├── server.py                  # FastAPI backend
│   ├── models/                    # SD Inpainting model
│   ├── ollama/                    # LLM enhancement
│   └── requirements.txt
├── frontend-flask/
│   ├── app_complete.py           # Flask app s všemi features
│   ├── database.py               # SQLite database operations
│   ├── templates/
│   │   ├── index_complete.html   # Kompletní GUI
│   │   └── print.html            # Print template
│   └── static/
│       └── results/              # Vygenerované obrázky
└── README.md
```

## 💾 Databáze Schema

### Table: `generations`
- `id` - Unique ID generování
- `person_name` - Jméno osoby
- `garment_name` - Název oblečení
- `person_image_path` - Cesta k fotce osoby
- `garment_image_path` - Cesta k fotce oblečení
- `result_image_path` - Cesta k výsledku
- `generation_type` - Typ varianty (local/cloud/paid)
- `generation_time` - Čas generování v sekundách
- `rating` - Hodnocení 0-5 hvězdiček
- `cost` - Cena generování v USD
- `status` - pending/processing/completed/failed
- `created_at` - Datum a čas vytvoření

### Table: `generation_variants`
- `name` - Jedinečný název varianty
- `display_name` - Zobrazovaný název
- `is_paid` - Placená varianta?
- `cost_per_generation` - Cena za generování
- `is_enabled` - Je aktivní?
- `avg_time` - Průměrný čas generování
- `max_time` - Maximum času (180s)
- `is_blacklisted` - Auto-blacklist při >3 min
- `blacklist_reason` - Důvod blacklistu

## 🎯 API Endpoints

### Frontend API
- `GET /` - Hlavní stránka s GUI
- `POST /upload` - Upload a generování
- `GET /api/generations` - Všechna generování
- `GET /api/generation/<id>` - Detail generování
- `POST /api/generation/<id>/rating` - Update rating
- `DELETE /api/generation/<id>` - Smazat generování
- `GET /api/variants` - Dostupné varianty
- `POST /api/remove-background` - Odstranit pozadí
- `GET /print/<id>` - Print view
- `GET /health` - Health check

### Backend API
- `POST /api/tryon` - Virtual try-on inference
- `GET /health` - Backend health

## 🖼️ Input Methods

### Osoba (Person)
1. **File Upload** - Nahrajte JPG/PNG soubor
2. **Webcam** - Vyfotit přímo z webkamery
3. **Historie** - Klikněte na předchozí generování v sidebaru

### Oblečení (Garment)
1. **File Upload** - Nahrajte JPG/PNG soubor
2. **Webcam** - Vyfotit přímo z webkamery
3. **URL** - Zadejte URL obrázku (automatické stahování)
4. **Remove Background** - Checkbox pro automatické odstranění pozadí
5. **Historie** - Klikněte na předchozí generování v sidebaru

## 🔧 Technologie

- **Backend**: FastAPI, PyTorch 2.9, Stable Diffusion Inpainting, Ollama
- **Frontend**: Flask, SQLite, JavaScript (Webcam API)
- **Image Processing**: PIL, rembg (background removal)
- **Database**: SQLite3 s row_factory pro dict results
- **ML**: MPS (Metal Performance Shaders) pro Apple Silicon M1/M2/M3/M4

## ⚙️ Konfigurace

### Porty
- Backend API: `8000`
- Frontend GUI: `5001`

### Limity
- Max upload size: `50MB`
- Max generation time: `180s` (3 minuty)
- Auto-blacklist při překročení avg času >180s

### Databáze
- SQLite soubor: `frontend-flask/virtual_fitting_room.db`
- Auto-inicializace při prvním spuštění

## 📊 Generation Variants

| Varianta | Typ | Cena | Avg Čas | Popis |
|----------|-----|------|---------|-------|
| Local Free | Free | $0.00 | ~45s | Lokální SD Inpainting |
| Local Premium | Paid | $0.50 | ~30s | Lokální s optimalizacemi |
| Cloud Free | Free | $0.00 | ~60s | Cloud API zdarma |
| Cloud Premium | Paid | $1.00 | ~20s | Cloud API premium |

## 🖨️ Print Functionality

Print view zobrazuje:
- **Input Images**: Osoba a oblečení vedle sebe s názvy
- **Result Image**: Velký výsledek uprostřed
- **Metadata Table**:
  - Datum a čas generování
  - ID generování
  - Typ generování
  - Čas generování (sekundy)
  - Cena
  - Hodnocení (hvězdičky)

## 🎨 GUI Features

### Sidebar (Left)
- Historie všech generování
- Kliknutelné items pro načtení do formuláře
- Zobrazení ratingu, času, typu
- Scroll pro dlouhé seznamy

### Main Panel (Center)
- Variant selector s pricing
- Person input (name, upload, webcam)
- Garment input (name, upload, webcam, URL, remove bg)
- Generate button s progress
- Result preview s rating stars
- Print button

### Webcam Modal
- Live video preview
- Capture button
- Preview captured image
- Cancel option

## 📝 Development Notes

- **Database migrations**: Automaticky při init_db()
- **File cleanup**: Automatické mazání při delete generation
- **Time tracking**: Moving average (80% old, 20% new)
- **Base64 encoding**: Pro webcam captures
- **CORS**: Nakonfigurováno pro localhost

## 🔍 Troubleshooting

### Backend nespouští
```bash
# Zkontrolujte port 8000
lsof -ti:8000 | xargs kill
# Restart
cd backend && uvicorn server:app --host 0.0.0.0 --port 8000
```

### Frontend nespouští
```bash
# Zkontrolujte port 5001
lsof -ti:5001 | xargs kill
# Restart
cd frontend-flask && python app_complete.py
```

### Webcam nefunguje
- Použijte HTTPS nebo localhost (browser security)
- Povolte camera permissions v browser
- Zkontrolujte console errors (F12)

### Background removal je pomalé
- rembg používá ML model (první run stahuje model)
- Druhý+ run je rychlejší (model v cache)

## 📄 License

Private project - All rights reserved

## 👤 Author

MAJ - Virtual Fitting Room Complete XL Edition - 2024

---

**Status**: ✅ Production Ready
**Version**: 2.0 Complete XL
**Last Updated**: November 2024
