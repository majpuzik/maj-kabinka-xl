#!/usr/bin/env python3
"""
Virtual Fitting Room - FastAPI Server
Starter template pro virtuální zkoušecí kabinku
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import torch
from PIL import Image
import io
import os
from pathlib import Path
import uuid

# Import custom modules (budou vytvořené)
from models.try_on import TryOnModel
from ollama.llm_helper import OllamaHelper

app = FastAPI(
    title="Virtual Fitting Room API",
    description="AI-powered virtual try-on aplikace",
    version="1.0.0"
)

# CORS pro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # V production nastavit konkrétní domény
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
OUTPUT_DIR = Path("./outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize models (lazy loading)
try_on_model = None
ollama_helper = None


@app.on_event("startup")
async def startup_event():
    """Initialize models při startu serveru"""
    global try_on_model, ollama_helper

    import platform as plat

    print("\n" + "="*60)
    print("🚀 VIRTUAL FITTING ROOM - STARTUP")
    print("="*60)

    # Platform detection
    print("\n📊 PLATFORM DETECTION:")
    print(f"  OS: {plat.system()} {plat.release()}")
    print(f"  Architecture: {plat.machine()}")
    print(f"  Python: {plat.python_version()}")

    # GPU detection
    print("\n🎮 GPU DETECTION:")
    if torch.backends.mps.is_available():
        print("  ✅ Apple Silicon (MPS) - Mac M1/M2/M3/M4 detected!")
        print("  🍎 Optimalizace: float32, 384px, attention slicing")
        device_type = "MPS"
    elif torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  ✅ NVIDIA CUDA - {gpu_name} detected!")
        print(f"  🎮 VRAM: {vram_gb:.1f} GB")
        print(f"  🎮 Optimalizace: float16, 512px")
        device_type = "CUDA"
    else:
        print("  ⚠️  Žádné GPU - používám CPU (bude VELMI pomalé!)")
        print("  💻 Doporučuji Mac M1+ nebo NVIDIA GPU")
        device_type = "CPU"

    print(f"\n{'='*60}")
    print(f"🔧 LOADING MODELS (device={device_type})...")
    print(f"{'='*60}\n")

    # Try-on model (s auto-detekcí device)
    try:
        try_on_model = TryOnModel(device="auto")  # automaticky vybere MPS/CUDA/CPU
        print("\n✅ Try-on model načten úspěšně!")
    except Exception as e:
        print(f"\n❌ Try-on model CHYBA: {e}")
        print("   Server bude omezený!")

    # Ollama helper
    print("\n🤖 OLLAMA DETECTION:")
    try:
        ollama_helper = OllamaHelper()
        if ollama_helper.is_available():
            models = ollama_helper.list_models()
            print(f"  ✅ Ollama server připojen!")
            print(f"  📦 Dostupné modely: {', '.join(models[:3])}...")
        else:
            print("  ⚠️  Ollama server nedostupný")
            print("  💡 Spusť: ollama serve")
    except Exception as e:
        print(f"  ⚠️  Ollama chyba: {e}")

    print("\n" + "="*60)
    print("✅ SERVER READY!")
    print("="*60)
    print(f"🌐 API: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    print(f"🎨 Frontend: http://localhost:3000 (pokud běží)")
    print("="*60 + "\n")


@app.get("/")
async def root():
    """Health check endpoint with platform info"""
    import platform as plat

    # Detect device
    if torch.backends.mps.is_available():
        device = "mps"
        device_name = "Apple Silicon (MPS)"
    elif torch.cuda.is_available():
        device = "cuda"
        device_name = torch.cuda.get_device_name(0)
    else:
        device = "cpu"
        device_name = "CPU"

    return {
        "status": "running",
        "service": "Virtual Fitting Room API",
        "version": "1.0.0",
        "platform": {
            "os": plat.system(),
            "architecture": plat.machine(),
            "python": plat.python_version(),
            "device": device,
            "device_name": device_name
        },
        "models": {
            "try_on": try_on_model is not None,
            "ollama": ollama_helper is not None and ollama_helper.is_available()
        }
    }


@app.get("/health")
async def health():
    """Simple health check endpoint"""
    return {
        "status": "OK",
        "models_loaded": try_on_model is not None
    }


@app.post("/api/tryon")
async def try_on(
    person_image: UploadFile = File(..., description="Fotografie osoby (celé tělo)"),
    garment_image: UploadFile = File(..., description="Fotografie oblečení"),
    use_ollama: bool = True
):
    """
    Hlavní endpoint pro virtual try-on

    Args:
        person_image: JPG/PNG fotografie osoby
        garment_image: JPG/PNG fotografie oblečení
        use_ollama: Použít Ollama pro prompt enhancement

    Returns:
        JSON s URL výsledného obrázku
    """

    if not try_on_model:
        raise HTTPException(status_code=503, detail="Try-on model není načten")

    try:
        # Load images
        person_img = Image.open(io.BytesIO(await person_image.read())).convert("RGB")
        garment_img = Image.open(io.BytesIO(await garment_image.read())).convert("RGB")

        # Ollama enhancement (optional)
        enhanced_prompt = None
        garment_analysis = None

        if use_ollama and ollama_helper and ollama_helper.is_available():
            print("🤖 Analyzuji oblečení pomocí Ollama...")

            # Ulož dočasně garment pro analýzu
            temp_garment_path = OUTPUT_DIR / f"temp_{uuid.uuid4()}.jpg"
            garment_img.save(temp_garment_path)

            # Analýza oblečení
            garment_analysis = ollama_helper.analyze_garment(str(temp_garment_path))

            # Generuj enhanced prompt
            enhanced_prompt = ollama_helper.generate_prompt(
                garment_analysis,
                "osoba na fotce"
            )

            # Cleanup temp
            temp_garment_path.unlink()

            print(f"📝 Enhanced prompt: {enhanced_prompt}")

        # Run try-on
        print("🎨 Generuji try-on výsledek...")
        result_image = try_on_model.generate(
            person_img,
            garment_img,
            prompt=enhanced_prompt
        )

        # Save result
        result_filename = f"result_{uuid.uuid4()}.jpg"
        result_path = OUTPUT_DIR / result_filename
        result_image.save(result_path, quality=95)

        return JSONResponse({
            "success": True,
            "result_url": f"/outputs/{result_filename}",
            "garment_analysis": garment_analysis,
            "enhanced_prompt": enhanced_prompt
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při zpracování: {str(e)}")


@app.post("/api/tryon/multiview")
async def try_on_multiview(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    num_views: int = 8
):
    """
    Generuj multi-view výsledky pro 3D rotaci

    Args:
        person_image: Fotografie osoby
        garment_image: Fotografie oblečení
        num_views: Počet pohledů (doporučeno 8)

    Returns:
        JSON s URLs všech pohledů
    """

    # TODO: Implementovat multi-view generaci
    raise HTTPException(status_code=501, detail="Multi-view zatím není implementován")


@app.post("/api/analyze-garment")
async def analyze_garment(
    garment_image: UploadFile = File(...)
):
    """
    Analyzuj oblečení pomocí Ollama LLaVA

    Returns:
        JSON s analýzou (typ, barva, materiál, styl)
    """

    if not ollama_helper or not ollama_helper.is_available():
        raise HTTPException(status_code=503, detail="Ollama není dostupný")

    try:
        # Save temp
        garment_img = Image.open(io.BytesIO(await garment_image.read()))
        temp_path = OUTPUT_DIR / f"temp_{uuid.uuid4()}.jpg"
        garment_img.save(temp_path)

        # Analyze
        analysis = ollama_helper.analyze_garment(str(temp_path))

        # Optional: styling tips
        # styling = ollama_helper.suggest_styling("...")

        # Cleanup
        temp_path.unlink()

        return JSONResponse({
            "success": True,
            "analysis": analysis
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/outputs/{filename}")
async def get_output(filename: str):
    """Serve výsledné obrázky"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    return FileResponse(file_path)


if __name__ == "__main__":
    import uvicorn

    print("""
    ╔═══════════════════════════════════════════════╗
    ║   Virtual Fitting Room API Server            ║
    ║   🎨 AI-Powered Virtual Try-On                ║
    ╚═══════════════════════════════════════════════╝
    """)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Hot reload pro development
    )
