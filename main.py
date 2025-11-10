"""
FastAPI pozadinska aplikacija za Generator priča za djecu.

Ova aplikacija omogućava korisnicima da otpreme dječje crteže i generiraju priče na bosanskom jeziku
koristeći OpenRouter API s modelom Polaris Alpha.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import uuid
from typing import Optional
import base64
import openai

# Učitavanje varijabli okruženja iz .env datoteke
from dotenv import load_dotenv
load_dotenv()

from story_generator import get_story_prompt

app = FastAPI(title="API za Generator priča za djecu")

# Povezivanje statičkih datoteka
app.mount("/static", StaticFiles(directory="static"), name="static")

# Postavljanje šablona (templates)
templates = Jinja2Templates(directory="templates")

# Kreiranje potrebnih direktorija ako ne postoje
Path("uploads").mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Prikazuje glavnu stranicu web interfejsa."""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


async def generate_story_with_openrouter_api(image_data: bytes, mime_type: str, child_name: str, style: str, length: str) -> str:
    """Generira priču koristeći OpenRouter API (model Polaris Alpha) na osnovu podataka o slici iz memorije."""
    try:
        # Konfiguracija OpenAI klijenta za korištenje OpenRoutera
        client = openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        )

        # Kodiranje slike u base64 format za API poziv
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Kreiranje upita (prompta)
        prompt = get_story_prompt(child_name, style, length, "priloženog crteža")
        
        # Pozivanje OpenRouter API-ja s mogućnošću obrade slika
        response = await client.chat.completions.create(
            model="openrouter/polaris-alpha",  # Korištenje modela Polaris Alpha putem OpenRoutera
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        return response.choices[0].message.content

    except Exception as e:
        # Proslijeđuje izuzetak da se obradi na višem nivou
        raise e


@app.post("/generate-story/")
async def generate_story(
    image: UploadFile = File(...),
    child_name: str = Form(...),
    style: str = Form(...),
    length: str = Form(...)
):
    """Generira priču na osnovu otpremljene slike i korisničkih postavki."""
    # Validacija ulaznih podataka
    if not child_name.strip():
        raise HTTPException(status_code=400, detail="Ime djeteta ne može biti prazno.")

    valid_styles = ["fairy tale", "sci-fi", "adventure", "mystery", "comedy", "everyday life"]
    if style not in valid_styles:
        raise HTTPException(status_code=400, detail="Nevažeći stil priče.")

    if length not in ["short", "long"]:
        raise HTTPException(status_code=400, detail="Nevažeća dužina priče.")

    # Validacija tipa datoteke
    file_extension = Path(image.filename).suffix.lower()
    if file_extension not in [".jpg", ".jpeg", ".png", ".bmp", ".webp"]:
        raise HTTPException(status_code=400, detail="Nepodržan format slike.")

    # Definisanje MIME tipova
    mime_type_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }

    mime_type = mime_type_map.get(file_extension)
    if not mime_type:
        raise HTTPException(status_code=400, detail="Nepodržan format slike.")

    try:
        # Čitanje sadržaja slikovne datoteke
        image_content = await image.read()

        # Generiranje priče pomoću API funkcije
        story = await generate_story_with_openrouter_api(image_content, mime_type, child_name, style, length)

        return {"story": story}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Greška prilikom generiranja priče: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Endpoint za provjeru statusa aplikacije (health check)."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)