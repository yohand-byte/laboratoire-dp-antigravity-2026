"""
Solar 3D Visualizer - Solution Métier Complète
===============================================

Utilise Google Solar API + Street View pour générer :
1. Image avec panneaux solaires (2D)
2. Visualisation 3D interactive (HTML/Three.js)
3. Données techniques pour DP

Auteur: Solaire Facile
"""

import requests
import json
import math
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


@dataclass
class SolarPanel:
    """Un panneau solaire avec sa position"""
    latitude: float
    longitude: float
    orientation: str  # PORTRAIT ou LANDSCAPE
    segment_index: int
    yearly_energy_kwh: float


@dataclass
class RoofSegment:
    """Un segment de toit"""
    pitch_degrees: float
    azimuth_degrees: float
    area_m2: float
    panels_count: int


@dataclass
class BuildingData:
    """Données complètes d'un bâtiment"""
    name: str
    center_lat: float
    center_lng: float
    max_panels: int
    roof_area_m2: float
    max_sunshine_hours: float
    segments: List[RoofSegment]
    panels: List[SolarPanel]
    panel_width_m: float = 1.045
    panel_height_m: float = 1.879


class GoogleSolarAPI:
    """Client pour Google Solar API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://solar.googleapis.com/v1"
    
    def get_building_insights(self, lat: float, lng: float) -> Optional[BuildingData]:
        """Récupère les données solaires d'un bâtiment"""
        url = f"{self.base_url}/buildingInsights:findClosest"
        params = {
            "location.latitude": lat,
            "location.longitude": lng,
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 404:
            print(f"ERREUR: Bâtiment non trouvé à {lat}, {lng}")
            print("Cette zone n'est peut-être pas couverte par Google Solar API")
            return None
        
        if response.status_code != 200:
            print(f"ERREUR API: {response.status_code}")
            print(response.text)
            return None
        
        data = response.json()
        solar = data.get("solarPotential", {})
        
        # Extraire les segments de toit
        segments = []
        for seg in solar.get("roofSegmentStats", []):
            segments.append(RoofSegment(
                pitch_degrees=seg.get("pitchDegrees", 0),
                azimuth_degrees=seg.get("azimuthDegrees", 0),
                area_m2=seg.get("stats", {}).get("areaMeters2", 0),
                panels_count=0
            ))
        
        # Extraire les panneaux
        panels = []
        for p in solar.get("solarPanels", []):
            center = p.get("center", {})
            panels.append(SolarPanel(
                latitude=center.get("latitude", 0),
                longitude=center.get("longitude", 0),
                orientation=p.get("orientation", "PORTRAIT"),
                segment_index=p.get("segmentIndex", 0),
                yearly_energy_kwh=p.get("yearlyEnergyDcKwh", 0)
            ))
        
        return BuildingData(
            name=data.get("name", ""),
            center_lat=data.get("center", {}).get("latitude", lat),
            center_lng=data.get("center", {}).get("longitude", lng),
            max_panels=solar.get("maxArrayPanelsCount", 0),
            roof_area_m2=solar.get("wholeRoofStats", {}).get("areaMeters2", 0),
            max_sunshine_hours=solar.get("maxSunshineHoursPerYear", 0),
            segments=segments,
            panels=panels,
            panel_width_m=solar.get("panelWidthMeters", 1.045),
            panel_height_m=solar.get("panelHeightMeters", 1.879)
        )


def get_street_view_url(lat: float, lng: float, api_key: str, 
                        heading: float = 0, pitch: float = 10, 
                        size: str = "800x600") -> str:
    """Génère l'URL Street View"""
    return (
        f"https://maps.googleapis.com/maps/api/streetview"
        f"?size={size}"
        f"&location={lat},{lng}"
        f"&heading={heading}"
        f"&pitch={pitch}"
        f"&key={api_key}"
    )


def download_street_view(lat: float, lng: float, api_key: str, 
                         output_path: str, heading: float = 0) -> bool:
    """Télécharge l'image Street View"""
    url = get_street_view_url(lat, lng, api_key, heading=heading, size="1200x800")
    response = requests.get(url)
    
    if response.status_code == 200 and len(response.content) > 1000:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    return False


def generate_3d_viewer_html(building: BuildingData, num_panels: int, 
                            output_path: str, api_key: str) -> str:
    """Génère une page HTML avec visualisation 3D Three.js"""
    
    # Prendre les N premiers panneaux
    selected_panels = building.panels[:num_panels]
    
    # Convertir les coordonnées GPS en coordonnées locales (mètres)
    # 1 degré latitude ≈ 111320 mètres
    # 1 degré longitude ≈ 111320 * cos(latitude) mètres
    center_lat = building.center_lat
    center_lng = building.center_lng
    lat_to_m = 111320
    lng_to_m = 111320 * math.cos(math.radians(center_lat))
    
    panels_js = []
    for p in selected_panels:
        x = (p.longitude - center_lng) * lng_to_m
        z = (p.latitude - center_lat) * lat_to_m
        panels_js.append({
            "x": round(x, 3),
            "z": round(z, 3),
            "orientation": p.orientation
        })
    
    # Récupérer l'azimuth du premier segment
    azimuth = building.segments[0].azimuth_degrees if building.segments else 180
    pitch = building.segments[0].pitch_degrees if building.segments else 20
    
    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visualisation 3D - Installation Solaire</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #1a1a2e; color: white; }}
        #container {{ width: 100vw; height: 100vh; }}
        #info {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(0,0,0,0.8);
            padding: 20px;
            border-radius: 10px;
            max-width: 350px;
        }}
        #info h1 {{ font-size: 1.5em; margin-bottom: 10px; color: #4CAF50; }}
        #info p {{ margin: 5px 0; font-size: 0.9em; }}
        #info .value {{ color: #4CAF50; font-weight: bold; }}
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            padding: 15px 30px;
            border-radius: 10px;
        }}
        #controls span {{ margin: 0 15px; }}
        .logo {{
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 1.2em;
            color: #4CAF50;
        }}
    </style>
</head>
<body>
    <div id="container"></div>
    
    <div id="info">
        <h1>☀️ Installation Solaire</h1>
        <p>Panneaux: <span class="value">{num_panels}</span></p>
        <p>Surface toit: <span class="value">{building.roof_area_m2:.1f} m²</span></p>
        <p>Orientation: <span class="value">{azimuth:.0f}° ({get_cardinal(azimuth)})</span></p>
        <p>Inclinaison: <span class="value">{pitch:.1f}°</span></p>
        <p>Production estimée: <span class="value">{sum(p.yearly_energy_kwh for p in selected_panels):.0f} kWh/an</span></p>
        <p>Heures soleil/an: <span class="value">{building.max_sunshine_hours:.0f}h</span></p>
    </div>
    
    <div class="logo">SOLAIRE FACILE</div>
    
    <div id="controls">
        <span>🖱️ Clic + Glisser: Rotation</span>
        <span>🔍 Molette: Zoom</span>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        // Configuration
        const PANELS = {json.dumps(panels_js)};
        const AZIMUTH = {azimuth};
        const PITCH = {pitch};
        const PANEL_WIDTH = {building.panel_width_m};
        const PANEL_HEIGHT = {building.panel_height_m};
        
        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x87CEEB);
        
        const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
        camera.position.set(15, 12, 15);
        camera.lookAt(0, 0, 0);
        
        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.shadowMap.enabled = true;
        document.getElementById('container').appendChild(renderer.domElement);
        
        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        
        const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
        sunLight.position.set(10, 20, 10);
        sunLight.castShadow = true;
        scene.add(sunLight);
        
        // Ground
        const groundGeom = new THREE.PlaneGeometry(50, 50);
        const groundMat = new THREE.MeshLambertMaterial({{ color: 0x228B22 }});
        const ground = new THREE.Mesh(groundGeom, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        scene.add(ground);
        
        // House base
        const houseGeom = new THREE.BoxGeometry(8, 5, 10);
        const houseMat = new THREE.MeshLambertMaterial({{ color: 0xF5F5DC }});
        const house = new THREE.Mesh(houseGeom, houseMat);
        house.position.y = 2.5;
        house.castShadow = true;
        scene.add(house);
        
        // Roof
        const roofGeom = new THREE.ConeGeometry(7, 4, 4);
        const roofMat = new THREE.MeshLambertMaterial({{ color: 0x8B4513 }});
        const roof = new THREE.Mesh(roofGeom, roofMat);
        roof.position.y = 7;
        roof.rotation.y = Math.PI / 4;
        roof.castShadow = true;
        scene.add(roof);
        
        // Solar panels
        const panelGeom = new THREE.BoxGeometry(PANEL_WIDTH, 0.05, PANEL_HEIGHT);
        const panelMat = new THREE.MeshPhongMaterial({{ 
            color: 0x1a1a3a,
            specular: 0x4444ff,
            shininess: 80
        }});
        
        const panelGroup = new THREE.Group();
        
        PANELS.forEach((p, i) => {{
            const panel = new THREE.Mesh(panelGeom, panelMat);
            
            // Position sur le toit
            const row = Math.floor(i / 4);
            const col = i % 4;
            panel.position.x = (col - 1.5) * (PANEL_WIDTH + 0.1);
            panel.position.z = (row - 0.5) * (PANEL_HEIGHT + 0.1);
            panel.position.y = 0;
            
            // Frame
            const frameGeom = new THREE.EdgesGeometry(panelGeom);
            const frameMat = new THREE.LineBasicMaterial({{ color: 0xcccccc }});
            const frame = new THREE.LineSegments(frameGeom, frameMat);
            panel.add(frame);
            
            panelGroup.add(panel);
        }});
        
        // Position and rotate panel group on roof
        panelGroup.position.y = 6.5;
        panelGroup.rotation.x = -Math.PI / 2 + THREE.MathUtils.degToRad(PITCH);
        panelGroup.rotation.z = THREE.MathUtils.degToRad(AZIMUTH - 180);
        scene.add(panelGroup);
        
        // Chimney
        const chimneyGeom = new THREE.BoxGeometry(1, 2, 1);
        const chimneyMat = new THREE.MeshLambertMaterial({{ color: 0x8B0000 }});
        const chimney = new THREE.Mesh(chimneyGeom, chimneyMat);
        chimney.position.set(2, 8, 0);
        scene.add(chimney);
        
        // Mouse controls
        let isDragging = false;
        let previousMousePosition = {{ x: 0, y: 0 }};
        let cameraAngle = {{ theta: Math.PI / 4, phi: Math.PI / 4 }};
        let cameraDistance = 25;
        
        document.addEventListener('mousedown', () => isDragging = true);
        document.addEventListener('mouseup', () => isDragging = false);
        document.addEventListener('mousemove', (e) => {{
            if (isDragging) {{
                cameraAngle.theta += e.movementX * 0.01;
                cameraAngle.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.1, cameraAngle.phi - e.movementY * 0.01));
                updateCamera();
            }}
        }});
        
        document.addEventListener('wheel', (e) => {{
            cameraDistance = Math.max(10, Math.min(50, cameraDistance + e.deltaY * 0.05));
            updateCamera();
        }});
        
        function updateCamera() {{
            camera.position.x = cameraDistance * Math.sin(cameraAngle.phi) * Math.cos(cameraAngle.theta);
            camera.position.y = cameraDistance * Math.cos(cameraAngle.phi);
            camera.position.z = cameraDistance * Math.sin(cameraAngle.phi) * Math.sin(cameraAngle.theta);
            camera.lookAt(0, 3, 0);
        }}
        
        // Animation
        function animate() {{
            requestAnimationFrame(animate);
            renderer.render(scene, camera);
        }}
        animate();
        
        // Resize
        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def get_cardinal(azimuth: float) -> str:
    """Convertit l'azimuth en direction cardinale"""
    directions = [
        (0, "Nord"), (45, "Nord-Est"), (90, "Est"), (135, "Sud-Est"),
        (180, "Sud"), (225, "Sud-Ouest"), (270, "Ouest"), (315, "Nord-Ouest"), (360, "Nord")
    ]
    for angle, name in directions:
        if abs(azimuth - angle) < 22.5:
            return name
    return "Sud"


def generate_dp_data(building: BuildingData, num_panels: int) -> dict:
    """Génère les données pour le dossier DP"""
    selected_panels = building.panels[:num_panels]
    segment = building.segments[0] if building.segments else None
    
    return {
        "nombre_panneaux": num_panels,
        "surface_toit_m2": round(building.roof_area_m2, 2),
        "orientation_degres": round(segment.azimuth_degrees, 1) if segment else 0,
        "orientation_cardinal": get_cardinal(segment.azimuth_degrees) if segment else "Sud",
        "inclinaison_degres": round(segment.pitch_degrees, 1) if segment else 0,
        "production_annuelle_kwh": round(sum(p.yearly_energy_kwh for p in selected_panels), 0),
        "heures_soleil_an": round(building.max_sunshine_hours, 0),
        "dimensions_panneau": {
            "largeur_m": building.panel_width_m,
            "hauteur_m": building.panel_height_m
        },
        "coordonnees": {
            "latitude": building.center_lat,
            "longitude": building.center_lng
        }
    }


def main():
    if len(sys.argv) < 4:
        print("=" * 60)
        print("SOLAR 3D VISUALIZER - Solaire Facile")
        print("=" * 60)
        print()
        print("Usage:")
        print("  python solar_3d_visualizer.py <latitude> <longitude> <num_panels>")
        print()
        print("Exemple:")
        print("  python solar_3d_visualizer.py 43.326370 5.394495 12")
        print()
        print("Nécessite: GOOGLE_API_KEY en variable d'environnement")
        sys.exit(1)
    
    lat = float(sys.argv[1])
    lng = float(sys.argv[2])
    num_panels = int(sys.argv[3])
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("ERREUR: Variable GOOGLE_API_KEY non définie")
        print("Lancez: export GOOGLE_API_KEY=votre_clé")
        sys.exit(1)
    
    print("=" * 60)
    print("SOLAR 3D VISUALIZER")
    print("=" * 60)
    print(f"Coordonnées: {lat}, {lng}")
    print(f"Panneaux demandés: {num_panels}")
    print()
    
    # 1. Récupérer les données Solar API
    print("[1/4] Récupération données Google Solar API...")
    solar_api = GoogleSolarAPI(api_key)
    building = solar_api.get_building_insights(lat, lng)
    
    if not building:
        sys.exit(1)
    
    print(f"      ✓ Bâtiment trouvé: {building.name}")
    print(f"      ✓ Panneaux max: {building.max_panels}")
    print(f"      ✓ Surface toit: {building.roof_area_m2:.1f} m²")
    
    if num_panels > len(building.panels):
        print(f"      ⚠ Ajustement: {len(building.panels)} panneaux disponibles")
        num_panels = len(building.panels)
    
    # 2. Télécharger Street View
    print("[2/4] Téléchargement image Street View...")
    street_view_path = f"street_view_{lat}_{lng}.jpg"
    if download_street_view(lat, lng, api_key, street_view_path):
        print(f"      ✓ Sauvegardé: {street_view_path}")
    else:
        print("      ⚠ Street View non disponible")
    
    # 3. Générer visualisation 3D
    print("[3/4] Génération visualisation 3D...")
    html_path = f"solar_3d_{lat}_{lng}.html"
    generate_3d_viewer_html(building, num_panels, html_path, api_key)
    print(f"      ✓ Sauvegardé: {html_path}")
    
    # 4. Générer données DP
    print("[4/4] Génération données techniques...")
    dp_data = generate_dp_data(building, num_panels)
    json_path = f"solar_data_{lat}_{lng}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dp_data, f, indent=2, ensure_ascii=False)
    print(f"      ✓ Sauvegardé: {json_path}")
    
    print()
    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"Panneaux: {num_panels}")
    print(f"Production: {dp_data['production_annuelle_kwh']:.0f} kWh/an")
    print(f"Orientation: {dp_data['orientation_cardinal']} ({dp_data['orientation_degres']}°)")
    print(f"Inclinaison: {dp_data['inclinaison_degres']}°")
    print()
    print("Fichiers générés:")
    print(f"  - {html_path} (ouvrir dans un navigateur)")
    print(f"  - {json_path} (données techniques)")
    if os.path.exists(street_view_path):
        print(f"  - {street_view_path} (photo Street View)")
    print()
    print("Pour voir la 3D: ouvrez le fichier HTML dans votre navigateur")


if __name__ == "__main__":
    main()
