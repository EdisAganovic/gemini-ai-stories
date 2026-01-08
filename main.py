"""
FastAPI pozadinska aplikacija za Generator priča za djecu.

Ova aplikacija omogućava korisnicima da otpreme dječje crteže i generiraju priče na bosanskom jeziku
koristeći Google Gemini API.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import os
import io
from typing import Optional

from google import genai
from PIL import Image
import base64

# Učitavanje varijabli okruženja iz .env datoteke
from dotenv import load_dotenv
load_dotenv()

# Globalna inicijalizacija Gemini klijenta
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    # Upozorenje ako ključ nije postavljen, ali dozvoljavamo aplikaciji da se pokrene
    print("WARNING: GEMINI_API_KEY nije postavljen u .env datoteci!")
    client = None
else:
    client = genai.Client(api_key=api_key)


def get_story_prompt(child_name: str, style: str, length: str, image_description: str) -> str:
    """Construct the prompt for story generation."""
    # Map English style names to Bosnian equivalents for use in the prompt
    style_mapping = {
        "fairy tale": "basna",
        "sci-fi": "naučna fantastika",
        "adventure": "pustolovina",
        "mystery": "misterija",
        "comedy": "komedija",
        "everyday life": "svakodnevni život"
    }
    
    bosnian_style = style_mapping.get(style, style)
    
    # Length description is already in Bosnian
    length_description = "5 paragrafa" if length == "short" else "10 paragrafa"

    prompt = f"""Napiši maštovitu i zanimljivu priču na bosanskom jeziku za dijete po imenu {child_name} na osnovu priloženog crteža: {image_description}.

Priča treba biti u stilu {bosnian_style} i sadržavati otprilike {length_description}.
Pobrini se da priča bude primjerena uzrastu djeteta, zabavna i da uključuje elemente koji se mogu vidjeti na crtežu.
Glavni lik priče treba biti {child_name} ili priča treba povezati crtež sa avanturom koju {child_name} doživljava.

Započni priču sa: "Jednom davno, {child_name} je otkrio/la..."
Za stil basne možeš započeti sa: "Priča se događa u jednom dalekom carstvu gdje živi..."
Završi priču sa: "...i tako se završila izuzetna avantura koju je doživio/la {child_name}!"

Učini priču kreativnom, pozitivnom i primjerenom za djecu. Sav tekst mora biti na bosanskom jeziku."""

    return prompt


app = FastAPI(title="API za Generator priča za djecu")

# Kreiranje potrebnih direktorija
Path("static").mkdir(parents=True, exist_ok=True)
Path("templates").mkdir(parents=True, exist_ok=True)

# Povezivanje statičkih datoteka - OVO JE POTREBNO ZA SERVIRANJE ASSETA
app.mount("/static", StaticFiles(directory="static"), name="static")

# Postavljanje šablona (templates)
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Prikazuje glavnu stranicu web interfejsa."""
    return templates.TemplateResponse("index.html", {"request": request})


async def generate_story_with_gemini_api(image_data: bytes, child_name: str, style: str, length: str) -> str:
    """Generira priču koristeći Google Gemini API na osnovu podataka o slici iz memorije."""
    try:
        if not client:
            raise ValueError("Gemini API klijent nije inicijaliziran. Provjerite API ključ.")

        # Kreiranje upita (prompta)
        prompt = get_story_prompt(child_name, style, length, "priloženog crteža")
        
        # Učitavanje slike iz bajtova
        image_file = io.BytesIO(image_data)
        img = Image.open(image_file)
        
        # Generiranje sadržaja pomoću novog API-ja
        # Koristimo run_in_executor jer je genai poziv sinhron
        from fastapi.concurrency import run_in_threadpool
        
        response = await run_in_threadpool(
            client.models.generate_content,
            model='gemini-flash-latest',
            contents=[prompt, img]
        )
        
        return response.text

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
        story = await generate_story_with_gemini_api(image_content, child_name, style, length)

        # Encode image to base64 for frontend display
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        return {
            "story": story,
            "image_base64": image_base64,
            "mime_type": mime_type
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Greška prilikom generiranja priče: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Endpoint za provjeru statusa aplikacije (health check)."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)