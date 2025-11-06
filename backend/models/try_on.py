"""
Try-On Model Wrapper - MAC M4 OPTIMIZED
Podporuje Apple Silicon (MPS) + NVIDIA CUDA + CPU fallback
"""

import torch
from PIL import Image
from typing import Optional
import os
import platform


class TryOnModel:
    """Wrapper pro různé try-on modely s Apple Silicon supportem"""

    def __init__(self, model_type="idm-vton", device="auto"):
        self.model_type = model_type
        self.device = self._get_best_device(device)
        self.pipe = None

        print(f"🔧 Inicializuji {model_type} model na {self.device}...")
        print(f"💻 Platform: {platform.system()} {platform.machine()}")
        self._load_model()

    def _get_best_device(self, device: str) -> str:
        """Automaticky detekuj nejlepší device (MPS pro Mac, CUDA pro NVIDIA, CPU fallback)"""

        if device != "auto":
            return device

        # Mac M1/M2/M3/M4 - použij MPS (Metal Performance Shaders)
        if torch.backends.mps.is_available():
            print("✅ Apple Silicon (MPS) detekován!")
            return "mps"

        # NVIDIA GPU - použij CUDA
        elif torch.cuda.is_available():
            print("✅ NVIDIA CUDA detekován!")
            return "cuda"

        # Fallback na CPU
        else:
            print("⚠️  Žádné GPU, používám CPU (bude pomalé)")
            return "cpu"

    def _load_model(self):
        """Load příslušný model podle typu"""

        if self.model_type == "idm-vton":
            self._load_idm_vton()
        elif self.model_type == "ootdiffusion":
            self._load_ootdiffusion()
        elif self.model_type == "sd-inpaint":
            self._load_sd_inpaint()
        else:
            raise ValueError(f"Neznámý model type: {self.model_type}")

    def _load_idm_vton(self):
        """Load IDM-VTON model (nejlepší kvalita)"""
        try:
            from diffusers import AutoPipelineForImage2Image

            # Check if model je stažený lokálně
            local_path = "./models/idm-vton"
            if os.path.exists(local_path):
                model_path = local_path
                print(f"✅ Načítám lokální model z {local_path}")
            else:
                model_path = "yisol/IDM-VTON"
                print(f"⚠️  Lokální model nenalezen, stahuji z HuggingFace...")
                print(f"   (toto může trvat několik minut při prvním spuštění)")

            # Mac M4: použij float32 pro MPS, float16 pro CUDA
            dtype = torch.float32 if self.device == "mps" else (torch.float16 if self.device == "cuda" else torch.float32)

            self.pipe = AutoPipelineForImage2Image.from_pretrained(
                model_path,
                torch_dtype=dtype
            ).to(self.device)

            # Optimalizace pro Mac M4
            if self.device == "mps":
                print("🍎 Optimalizuji pro Apple Silicon...")
                # MPS má problémy s některými operacemi, použij attention slicing
                self.pipe.enable_attention_slicing()
                # Redukuj memory usage
                # self.pipe.enable_vae_slicing()  # Někdy problematické na MPS

            print("✅ IDM-VTON model načten")

        except Exception as e:
            print(f"❌ Chyba při načítání IDM-VTON: {e}")
            print("   Zkouším fallback na SD inpainting...")
            self.model_type = "sd-inpaint"
            self._load_sd_inpaint()

    def _load_ootdiffusion(self):
        """Load OOTDiffusion model"""
        # TODO: Implementovat OOTDiffusion
        # https://github.com/levihsu/OOTDiffusion
        raise NotImplementedError("OOTDiffusion zatím není implementován")

    def _load_sd_inpaint(self):
        """Fallback: Stable Diffusion Inpainting"""
        try:
            from diffusers import StableDiffusionInpaintPipeline

            dtype = torch.float32 if self.device == "mps" else (torch.float16 if self.device == "cuda" else torch.float32)

            self.pipe = StableDiffusionInpaintPipeline.from_pretrained(
                "runwayml/stable-diffusion-inpainting",
                torch_dtype=dtype
            ).to(self.device)

            # Mac optimalizace
            if self.device == "mps":
                self.pipe.enable_attention_slicing()

            print("✅ SD Inpainting načten (fallback)")

        except Exception as e:
            raise RuntimeError(f"Nelze načíst žádný model: {e}")

    def generate(
        self,
        person_image: Image.Image,
        garment_image: Image.Image,
        prompt: Optional[str] = None,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5
    ) -> Image.Image:
        """
        Generuj try-on výsledek

        Args:
            person_image: PIL Image osoby
            garment_image: PIL Image oblečení
            prompt: Text prompt (optional, může být enhanced z Ollama)
            num_inference_steps: Počet kroků (vyšší = lepší kvalita, pomalejší)
            guidance_scale: Jak moc dodržovat prompt (7.5 je standard)

        Returns:
            PIL Image s výsledkem
        """

        # Default prompt
        if prompt is None:
            prompt = "a person wearing the garment, high quality, photorealistic, detailed"

        print(f"🎨 Generuji s promptem: {prompt}")
        print(f"⚙️  Device: {self.device}, Steps: {num_inference_steps}")

        # Resize pro konzistentní velikosti
        # Mac M4: použij menší size pokud MPS pro rychlejší inference
        max_size = 384 if self.device == "mps" else 512
        person_image = self._resize_image(person_image, max_size=max_size)
        garment_image = self._resize_image(garment_image, max_size=max_size)

        try:
            if self.model_type == "idm-vton":
                # IDM-VTON API
                result = self.pipe(
                    prompt=prompt,
                    image=person_image,
                    garment_image=garment_image,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale
                ).images[0]

            elif self.model_type == "sd-inpaint":
                # SD Inpainting (jednodušší, fallback)
                # Potřebujeme mask - zde zjednodušené (v production použij SAM)
                mask = self._create_simple_mask(person_image)

                result = self.pipe(
                    prompt=prompt,
                    image=person_image,
                    mask_image=mask,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale
                ).images[0]

            else:
                raise NotImplementedError(f"Generate není implementováno pro {self.model_type}")

        except RuntimeError as e:
            # MPS může mít problémy s některými operacemi
            if self.device == "mps" and "MPS" in str(e):
                print("⚠️  MPS chyba, zkouším s CPU...")
                self.device = "cpu"
                self.pipe = self.pipe.to("cpu")
                return self.generate(person_image, garment_image, prompt, num_inference_steps, guidance_scale)
            else:
                raise e

        return result

    def _resize_image(self, image: Image.Image, max_size: int = 512) -> Image.Image:
        """Resize image keeping aspect ratio"""
        w, h = image.size

        if max(w, h) > max_size:
            if w > h:
                new_w = max_size
                new_h = int(h * (max_size / w))
            else:
                new_h = max_size
                new_w = int(w * (max_size / h))

            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        return image

    def _create_simple_mask(self, image: Image.Image) -> Image.Image:
        """
        Vytvoř jednoduchou masku pro oblast oblečení
        V production použij Segment Anything Model (SAM)
        """
        import numpy as np

        # Zjednodušená verze - mask prostřední části těla
        w, h = image.size
        mask = np.zeros((h, w), dtype=np.uint8)

        # Obdélník pro horní část těla (přibližně)
        top = int(h * 0.2)
        bottom = int(h * 0.7)
        left = int(w * 0.25)
        right = int(w * 0.75)

        mask[top:bottom, left:right] = 255

        return Image.fromarray(mask)


# Helper pro stažení modelu předem
def download_models():
    """Utility pro předem stažení modelů"""
    print("📥 Stahuji modely...")

    from diffusers import AutoPipelineForImage2Image

    # IDM-VTON
    print("📥 IDM-VTON...")
    # Mac M4: použij float32
    dtype = torch.float32 if torch.backends.mps.is_available() else torch.float16
    pipe = AutoPipelineForImage2Image.from_pretrained(
        "yisol/IDM-VTON",
        torch_dtype=dtype
    )
    pipe.save_pretrained("./models/idm-vton")
    print("✅ IDM-VTON uložen do ./models/idm-vton")

    print("✅ Všechny modely staženy!")


# Mac M4 specific test
def test_mac_m4():
    """Test funkcionality na Mac M4"""
    print("🧪 Test pro Mac M4...")
    print(f"PyTorch version: {torch.__version__}")
    print(f"MPS available: {torch.backends.mps.is_available()}")
    print(f"MPS built: {torch.backends.mps.is_built()}")

    if torch.backends.mps.is_available():
        print("✅ MPS je připraveno!")
        # Test tensor
        x = torch.randn(100, 100).to("mps")
        y = x @ x.T
        print(f"✅ MPS test tensor operace úspěšná!")
        print(f"   Result shape: {y.shape}")
    else:
        print("❌ MPS není dostupné")


if __name__ == "__main__":
    # Test nebo download
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "download":
        download_models()
    elif len(sys.argv) > 1 and sys.argv[1] == "test-mac":
        test_mac_m4()
    else:
        # Test run
        print("🧪 Test try-on model...")
        model = TryOnModel()
        print("✅ Model inicializován úspěšně!")
