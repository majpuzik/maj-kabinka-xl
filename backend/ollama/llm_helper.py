"""
Ollama LLM Helper
Integrace s lokálním Ollama serverem pro:
- Analýzu obrázků oblečení (LLaVA)
- Generování enhanced promptů
- Styling doporučení
"""

import requests
import base64
from typing import Optional, Dict
from pathlib import Path


class OllamaHelper:
    """Helper pro komunikaci s Ollama serverem"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.vision_model = "llava"  # nebo "llama3.2-vision"
        self.text_model = "llama3.2"  # nebo jiný textový model

    def is_available(self) -> bool:
        """Check zda Ollama server běží"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> list:
        """Seznam dostupných modelů"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                return [m["name"] for m in response.json().get("models", [])]
            return []
        except:
            return []

    def analyze_garment(self, image_path: str) -> str:
        """
        Analyzuj oblečení na obrázku pomocí LLaVA

        Args:
            image_path: Cesta k obrázku oblečení

        Returns:
            Detailní textová analýza
        """

        # Load a enkóduj obrázek
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        # Prompt pro analýzu
        prompt = """Analyzuj toto oblečení detailně. Odpověz strukturovaně:

TYP: (tričko/košile/mikina/bunda/kalhoty/sukně/šaty/...)
BARVA: (hlavní barva a případné další barvy)
VZOR: (jednolitá/proužky/kostky/potisk/...)
MATERIÁL: (bavlna/denim/kůže/fleece/sportovní/...)
STYL: (casual/formal/sport/vintage/modern/...)
DETAILY: (límec/kapuce/knoflíky/zip/...)

Buď stručný ale přesný."""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.vision_model,
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json().get("response", "")
                return result.strip()
            else:
                return f"Chyba při analýze: {response.status_code}"

        except Exception as e:
            return f"Chyba: {str(e)}"

    def generate_prompt(
        self,
        garment_analysis: str,
        person_description: str = "osoba",
        style_preference: Optional[str] = None
    ) -> str:
        """
        Generuj optimalizovaný prompt pro try-on model

        Args:
            garment_analysis: Výstup z analyze_garment()
            person_description: Popis osoby (optional)
            style_preference: Preferovaný styl (optional)

        Returns:
            Enhanced prompt pro Stable Diffusion / IDM-VTON
        """

        system_prompt = f"""Jsi expert na generování promptů pro AI image generation.
Tvým úkolem je vytvořit optimální prompt pro virtual try-on model.

INFORMACE:
- Osoba: {person_description}
- Oblečení: {garment_analysis}
{f'- Styl preference: {style_preference}' if style_preference else ''}

Vytvoř prompt který zajistí:
1. Realistické padnutí oblečení na tělo
2. Správné světlo a stíny
3. Zachování textury materiálu
4. Anatomickou správnost
5. Fotorealistický výsledek

FORMÁT: Vrať pouze samotný prompt, bez vysvětlení nebo komentářů.
JAZYK: Anglický (pro AI modely)
DÉLKA: Max 75 slov

PROMPT:"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.text_model,
                    "prompt": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                # Očisti od případných úvodních/závěrečných poznámek
                return self._clean_prompt(result)
            else:
                # Fallback
                return self._fallback_prompt(garment_analysis)

        except Exception as e:
            print(f"⚠️  Ollama prompt gen chyba: {e}")
            return self._fallback_prompt(garment_analysis)

    def suggest_styling(self, garment_analysis: str) -> Dict[str, str]:
        """
        Navrhni styling tipy pro dané oblečení

        Args:
            garment_analysis: Analýza oblečení

        Returns:
            Dict s tipy
        """

        prompt = f"""Na základě tohoto oblečení poskytni styling rady:

OBLEČENÍ: {garment_analysis}

Odpověz ve formátu:

KOMBINACE: (s čím to dobře kombinovat)
PŘÍLEŽITOSTI: (kde/kdy to nosit)
DOPLŇKY: (doporučené doplňky)

Buď stručný, praktický, česky."""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.text_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20
            )

            if response.status_code == 200:
                result = response.json().get("response", "")
                return self._parse_styling_response(result)
            else:
                return {}

        except Exception as e:
            print(f"⚠️  Styling suggestions error: {e}")
            return {}

    def _clean_prompt(self, prompt: str) -> str:
        """Očisti prompt od nepotřebných částí"""
        # Odstranění úvodních frází
        prefixes_to_remove = [
            "prompt:",
            "here's the prompt:",
            "here is the prompt:",
            "the prompt:",
        ]

        prompt_lower = prompt.lower()
        for prefix in prefixes_to_remove:
            if prompt_lower.startswith(prefix):
                prompt = prompt[len(prefix):].strip()

        # Odstranění uvozovek
        prompt = prompt.strip('"\'')

        return prompt

    def _fallback_prompt(self, garment_analysis: str) -> str:
        """Fallback prompt když Ollama selže"""
        return f"A person wearing {garment_analysis}, photorealistic, high quality, detailed, proper fit, natural lighting, professional photo"

    def _parse_styling_response(self, response: str) -> Dict[str, str]:
        """Parse strukturovanou odpověď styling tipů"""
        result = {}

        lines = response.split("\n")
        current_key = None

        for line in lines:
            line = line.strip()

            if line.startswith("KOMBINACE:"):
                current_key = "combinations"
                result[current_key] = line.replace("KOMBINACE:", "").strip()
            elif line.startswith("PŘÍLEŽITOSTI:"):
                current_key = "occasions"
                result[current_key] = line.replace("PŘÍLEŽITOSTI:", "").strip()
            elif line.startswith("DOPLŇKY:"):
                current_key = "accessories"
                result[current_key] = line.replace("DOPLŇKY:", "").strip()
            elif current_key and line:
                result[current_key] += " " + line

        return result


# CLI test
if __name__ == "__main__":
    import sys

    helper = OllamaHelper()

    print("🔍 Testuji Ollama připojení...")
    if helper.is_available():
        print("✅ Ollama server běží!")
        print(f"📦 Dostupné modely: {', '.join(helper.list_models())}")

        # Test analýzy (pokud je zadán obrázek)
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
            print(f"\n🖼️  Analyzuji: {image_path}")

            analysis = helper.analyze_garment(image_path)
            print(f"\n📋 ANALÝZA:\n{analysis}")

            prompt = helper.generate_prompt(analysis)
            print(f"\n✨ ENHANCED PROMPT:\n{prompt}")

            styling = helper.suggest_styling(analysis)
            print(f"\n👔 STYLING TIPY:")
            for key, value in styling.items():
                print(f"  {key}: {value}")

    else:
        print("❌ Ollama server není dostupný!")
        print("   Spusť: ollama serve")
