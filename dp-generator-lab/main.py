"""
DP Generator Lab - Laboratoire de génération de Déclarations Préalables
=======================================================================

Application FastAPI modulaire combinant:
- Validation cartographique (HTML-CARTO API)
- Éditeur de calepinage 2D/3D (CALEPINAGE 3D REPLICA)
- Génération PDF DP Mairie

Auteur: Solaire Facile
"""

from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import os

app = FastAPI(
    title="DP Generator Lab",
    version="1.0.0",
    description="Laboratoire de génération de DP Mairie avec validation carto et calepinage 3D"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
HTML_CARTO_API = os.getenv("HTML_CARTO_API", "https://html-carto-api-29459740400.europe-west1.run.app")

# Templates
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


# ============================================================
# MODELS
# ============================================================

class ProjectAddress(BaseModel):
    adresse: str
    code_postal: str
    ville: str
    lat: Optional[float] = None
    lon: Optional[float] = None

class CadastreInfo(BaseModel):
    parcelle: str
    section: str
    contenance: Optional[float] = None

class TechnicalInfo(BaseModel):
    puissance_kwc: float
    nombre_panneaux: int
    orientation: str = "SUD"
    type_couverture: str = "Tuiles"
    surface_terrain: Optional[float] = None
    surface_plancher: Optional[float] = None

class DPProject(BaseModel):
    address: ProjectAddress
    cadastre: CadastreInfo
    technical: TechnicalInfo
    societe: str
    maitre_ouvrage: str


# ============================================================
# PAGES
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Page d'accueil du laboratoire"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "DP Generator Lab"}
    )


@app.get("/dp/", response_class=HTMLResponse)
async def dp_generator(request: Request):
    """Interface principale du générateur DP"""
    return templates.TemplateResponse(
        "dp_generator.html",
        {"request": request, "html_carto_api": HTML_CARTO_API}
    )


@app.get("/calepinage/", response_class=HTMLResponse) 
async def calepinage_editor(
    request: Request, 
    lat: float, 
    lon: float,
    adresse: str = "",
    cp: str = "",
    ville: str = "",
    societe: str = "SOLAIRE FACILE",
    maitreOuvrage: str = ""
):
    """Éditeur de calepinage interactif avec données réelles"""
    
    print(f"DEBUG: Requesting calepinage for {lat}, {lon}")
    
    # Récupérer les données via HTML-CARTO API
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Pour l'instant, on va demander 1500x1000px au 1:1000
        scale = "1:1000"
        print(f"DEBUG: Calling render-map with scale {scale}...")
        try:
            render_resp = await client.post(
                f"{HTML_CARTO_API}/api/render-map",
                json={
                    "lat": lat, 
                    "lon": lon, 
                    "scale": scale,
                    "width": 1600,
                    "height": 1000,
                    "layers": ["ortho"],
                    "show_scale_bar": False,
                    "show_compass": False
                }
            )
            print(f"DEBUG: render-map status: {render_resp.status_code}")
        except Exception as e:
            print(f"ERROR: render-map failed: {e}")
            render_resp = None
        
        b64_image = ""
        mpp = 0.264 # Par défaut pour 1:1000
        
        if render_resp and render_resp.status_code == 200:
            data = render_resp.json()
            full_b64 = data.get("image", "")
            print(f"DEBUG: Image received, length: {len(full_b64)}")
            if "," in full_b64:
                b64_image = full_b64.split(",")[1]
            else:
                b64_image = full_b64
            
            # MPP: 1:1000 => 0.264m/px, 1:500 => 0.132m/px
            mpp = 0.264 if scale == "1:1000" else 0.132
        else:
            print("ERROR: Failed to get map image")

    # Config JSON pour éviter erreurs JS
    cfg_data = {
        "lat": lat, 
        "lon": lon, 
        "mpp": mpp,
        "adresse": adresse,
        "cp": cp,
        "ville": ville,
        "societe": societe,
        "maitreOuvrage": maitreOuvrage
    }
    cfg_json = json.dumps(cfg_data)

    return templates.TemplateResponse(
        "calepinage_v3_template.html",
        {
            "request": request, 
            "cfg_json": cfg_json,
            "b64": b64_image,
            "pinfo": f"Lat: {lat:.6f}, Lon: {lon:.6f}"
        }
    )


# ============================================================
# API ENDPOINTS
# ============================================================

@app.get("/api/health")
async def health_check():
    """Vérification de santé de l'application"""
    return {"status": "ok", "service": "dp-generator-lab"}


@app.post("/api/validate-address")
async def validate_address(address: ProjectAddress):
    """
    Valide une adresse via HTML-CARTO API.
    Récupère les coordonnées GPS et les parcelles cadastrales.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Geocode si pas de coordonnées
        if not address.lat or not address.lon:
            geocode_resp = await client.get(
                f"{HTML_CARTO_API}/api/geocode",
                params={"q": f"{address.adresse} {address.code_postal} {address.ville}"}
            )
            if geocode_resp.status_code == 200:
                geo_data = geocode_resp.json()
                address.lat = geo_data.get("location", {}).get("lat")
                address.lon = geo_data.get("location", {}).get("lon")
        
        # 2. Valider la localisation
        if address.lat and address.lon:
            validation_resp = await client.post(
                f"{HTML_CARTO_API}/api/validate-location",
                json={"lat": address.lat, "lon": address.lon, "address": address.adresse}
            )
            if validation_resp.status_code == 200:
                return validation_resp.json()
        
        raise HTTPException(status_code=400, detail="Impossible de valider l'adresse")


@app.post("/api/update-location")
async def update_location(lat: float = Form(...), lon: float = Form(...)):
    """
    Met à jour la localisation après déplacement du marqueur.
    Récupère les nouvelles parcelles cadastrales.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        validation_resp = await client.post(
            f"{HTML_CARTO_API}/api/validate-location",
            json={"lat": lat, "lon": lon}
        )
        if validation_resp.status_code == 200:
            return validation_resp.json()
        raise HTTPException(status_code=400, detail="Erreur validation localisation")


@app.post("/api/render-map")
async def render_map_proxy(
    lat: float = Form(...),
    lon: float = Form(...),
    scale: str = Form("1:1000"),
    layers: str = Form("ortho,cadastre")
):
    """
    Proxy pour le rendu de carte via HTML-CARTO API.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        render_resp = await client.post(
            f"{HTML_CARTO_API}/api/render-map",
            json={
                "lat": lat,
                "lon": lon,
                "scale": scale,
                "layers": layers.split(","),
                "width": 800,
                "height": 600
            }
        )
        if render_resp.status_code == 200:
            return render_resp.json()
        raise HTTPException(status_code=500, detail="Erreur rendu carte")


@app.post("/api/generate-dp")
async def generate_dp(project: DPProject):
    """
    Génère le dossier DP complet.
    TODO: Intégrer la génération PDF ReportLab.
    """
    return {
        "success": True,
        "message": "Génération DP en cours de développement",
        "project": project.dict()
    }


from modules.pdf_generator import generate_complete_dp
import base64
from io import BytesIO

@app.post("/api/generate-pdf")
async def generate_pdf_endpoint(project_data: dict):
    """
    Génère le dossier PDF DP complet.
    Reçoit les données projet et les captures base64 de l'éditeur.
    """
    lat = project_data.get("lat")
    lon = project_data.get("lon")
    
    # 1. Collecte des images cartographiques via HTML-CARTO API
    images = {}
    
    # Images à récupérer
    map_configs = [
        ("aerial_1000", "1:1000", ["ortho"]),
        ("map_2000", "1:2000", ["ortho"]),
        ("map_5000", "1:5000", ["ortho"]),
        ("cadastre_1000", "1:1000", ["cadastre"]),
        ("cadastre_250", "1:500", ["cadastre"]), # On utilise 1:500 car 1:250 pas encore supporté par API
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for key, scale, layers in map_configs:
            try:
                resp = await client.post(
                    f"{HTML_CARTO_API}/api/render-map",
                    json={
                        "lat": lat, "lon": lon, "scale": scale,
                        "layers": layers, "width": 1600, "height": 1000
                    }
                )
                if resp.status_code == 200:
                    img_b64 = resp.json().get("image", "")
                    if "," in img_b64: img_b64 = img_b64.split(",")[1]
                    images[key] = base64.b64decode(img_b64)
            except Exception as e:
                print(f"Error fetching {key}: {e}")

    # 2. Ajout des images venant du client (calepinage, 3d)
    for key in ["calepinage", "3d"]:
        b64_data = project_data.get(f"image_{key}", "")
        if b64_data:
            if "," in b64_data: b64_data = b64_data.split(",")[1]
            images[key] = base64.b64decode(b64_data)

    # 3. Préparation des données pour ReportLab
    pdf_data = {
        "maitre_ouvrage": project_data.get("maitreOuvrage", "Client"),
        "adresse": project_data.get("adresse", ""),
        "cp": project_data.get("cp", ""),
        "ville": project_data.get("ville", ""),
        "societe": project_data.get("societe", "SOLAIRE FACILE"),
        "parcelle": project_data.get("parcelle", ""),
        "puissance": project_data.get("puissance", "3.0"),
        "nombre_panneaux": project_data.get("nbPanneaux", 0),
        "azimuth": project_data.get("azimuth", 180)
    }
    
    # 4. Génération effective
    output_filename = f"DP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join("/tmp", output_filename)
    
    try:
        generate_complete_dp(pdf_data, images, output_path)
        
        # Retourner le PDF en base64 ou via StreamingResponse
        from fastapi.responses import FileResponse
        return FileResponse(
            output_path, 
            media_type="application/pdf", 
            filename=output_filename
        )
    except Exception as e:
        print(f"PDF Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8080)
