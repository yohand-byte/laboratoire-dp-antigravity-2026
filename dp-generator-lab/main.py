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
async def calepinage_editor(request: Request, lat: float = 43.32637, lon: float = 5.394495):
    """Éditeur de calepinage interactif"""
    return templates.TemplateResponse(
        "calepinage_v3_template.html",
        {"request": request, "lat": lat, "lon": lon}
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


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
