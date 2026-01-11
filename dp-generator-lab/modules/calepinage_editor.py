"""
Éditeur de Calepinage Solaire Interactif
========================================

Utilise l'orthophoto réelle pour placer les panneaux un par un.

- Vue aérienne depuis html-carto.onrender.com
- Placement par clic
- Export image et données

Auteur: Solaire Facile
"""

import os
import sys
import json
import math
import requests
from io import BytesIO
from PIL import Image
import base64


def get_orthophoto_composite(lat: float, lon: float, zoom: int = 19, grid_size: int = 3) -> Image.Image:
    """
    Récupère une grille de tuiles orthophoto et les assemble
    grid_size=3 signifie 3x3 tuiles = 768x768 pixels
    """
    base_url = "https://html-carto.onrender.com/api/orthophoto/proxy"
    
    # Calculer la tuile centrale
    n = 2 ** zoom
    center_x = int((lon + 180) / 360 * n)
    center_y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    
    # Créer l'image composite
    tile_size = 256
    img_size = tile_size * grid_size
    composite = Image.new('RGB', (img_size, img_size))
    
    offset = grid_size // 2
    
    print(f"    Téléchargement {grid_size}x{grid_size} tuiles zoom {zoom}...")
    
    for dy in range(-offset, offset + 1):
        for dx in range(-offset, offset + 1):
            tile_x = center_x + dx
            tile_y = center_y + dy
            
            # Calculer lat/lon de cette tuile pour le proxy
            tile_lon = tile_x / n * 360 - 180
            tile_lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n))))
            
            try:
                resp = requests.get(
                    base_url,
                    params={"lon": tile_lon, "lat": tile_lat, "zoom": zoom},
                    timeout=30
                )
                if resp.status_code == 200 and resp.headers.get('content-type', '').startswith('image'):
                    tile_img = Image.open(BytesIO(resp.content))
                    px = (dx + offset) * tile_size
                    py = (dy + offset) * tile_size
                    composite.paste(tile_img, (px, py))
            except Exception as e:
                print(f"      Erreur tuile {dx},{dy}: {e}")
    
    return composite


def get_parcelle_geometry(lat: float, lon: float) -> dict:
    """Récupère la géométrie de la parcelle"""
    url = "https://html-carto.onrender.com/api/cadastre/parcelle"
    try:
        resp = requests.get(url, params={"lon": lon, "lat": lat}, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def generate_panel_editor_html(
    lat: float, 
    lon: float, 
    orthophoto_base64: str,
    parcelle_data: dict,
    output_path: str
) -> str:
    """Génère l'éditeur HTML interactif"""
    
    parcelle_info = ""
    if parcelle_data and parcelle_data.get("success"):
        p = parcelle_data.get("parcelle", {})
        parcelle_info = f"""
        Section: {p.get('section', 'N/A')}<br>
        Numéro: {p.get('numero', 'N/A')}<br>
        Surface: {p.get('contenance', 'N/A')} m²<br>
        Commune: {p.get('nom_commune', 'N/A')}
        """
    
    html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calepinage Solaire - Éditeur Interactif</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white; 
            min-height: 100vh;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
        }}
        
        .sidebar {{
            width: 320px;
            background: rgba(0,0,0,0.8);
            padding: 20px;
            overflow-y: auto;
            border-right: 1px solid #333;
        }}
        
        .main {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        
        h1 {{
            font-size: 1.4em;
            color: #4CAF50;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #4CAF50;
        }}
        
        h2 {{
            font-size: 1.1em;
            color: #2196F3;
            margin: 20px 0 10px;
        }}
        
        .info-box {{
            background: #222;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 0.9em;
            line-height: 1.6;
        }}
        
        .stat {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #333;
        }}
        .stat:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #888; }}
        .stat-value {{ color: #4CAF50; font-weight: bold; }}
        
        #canvas-container {{
            position: relative;
            border: 3px solid #4CAF50;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }}
        
        #editor-canvas {{
            display: block;
            cursor: crosshair;
        }}
        
        .toolbar {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        .btn {{
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: bold;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .btn-primary {{
            background: #4CAF50;
            color: white;
        }}
        .btn-primary:hover {{ background: #45a049; }}
        
        .btn-secondary {{
            background: #2196F3;
            color: white;
        }}
        .btn-secondary:hover {{ background: #1976D2; }}
        
        .btn-danger {{
            background: #f44336;
            color: white;
        }}
        .btn-danger:hover {{ background: #d32f2f; }}
        
        .btn-outline {{
            background: transparent;
            border: 2px solid #666;
            color: #fff;
        }}
        .btn-outline:hover {{ border-color: #4CAF50; color: #4CAF50; }}
        
        .control-group {{
            margin: 15px 0;
        }}
        .control-group label {{
            display: block;
            margin-bottom: 8px;
            color: #aaa;
            font-size: 0.9em;
        }}
        .control-group input[type="range"] {{
            width: 100%;
        }}
        .control-group select {{
            width: 100%;
            padding: 10px;
            border-radius: 5px;
            background: #333;
            color: white;
            border: 1px solid #555;
        }}
        
        .range-value {{
            text-align: center;
            font-size: 1.5em;
            color: #4CAF50;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .panel-list {{
            max-height: 200px;
            overflow-y: auto;
            background: #1a1a1a;
            border-radius: 8px;
            padding: 10px;
        }}
        
        .panel-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            margin: 5px 0;
            background: #2a2a2a;
            border-radius: 5px;
            font-size: 0.85em;
        }}
        
        .panel-item .delete-btn {{
            background: #f44336;
            border: none;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }}
        
        .mode-indicator {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.8);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.85em;
        }}
        .mode-indicator.add {{ color: #4CAF50; }}
        .mode-indicator.select {{ color: #2196F3; }}
        
        .coords {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.8em;
            font-family: monospace;
        }}
        
        .logo {{
            text-align: center;
            padding: 20px;
            color: #4CAF50;
            font-weight: bold;
            font-size: 1.1em;
            border-top: 1px solid #333;
            margin-top: auto;
        }}
        
        .help-text {{
            font-size: 0.85em;
            color: #888;
            margin-top: 10px;
            padding: 10px;
            background: #1a1a1a;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>☀️ Calepinage Solaire</h1>
            
            <div class="info-box">
                <strong>📍 Localisation</strong><br>
                Lat: {lat}<br>
                Lon: {lon}
            </div>
            
            <div class="info-box">
                <strong>📋 Parcelle</strong><br>
                {parcelle_info if parcelle_info else "Non disponible"}
            </div>
            
            <h2>📊 Statistiques</h2>
            <div class="info-box">
                <div class="stat">
                    <span class="stat-label">Panneaux placés</span>
                    <span class="stat-value" id="panel-count">0</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Puissance</span>
                    <span class="stat-value" id="power">0 kWc</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Production est.</span>
                    <span class="stat-value" id="production">0 kWh/an</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Surface</span>
                    <span class="stat-value" id="surface">0 m²</span>
                </div>
            </div>
            
            <h2>⚙️ Configuration</h2>
            
            <div class="control-group">
                <label>Taille panneau</label>
                <select id="panel-size">
                    <option value="1.7,1.0">Standard (1.7m × 1.0m)</option>
                    <option value="2.0,1.0">Grand (2.0m × 1.0m)</option>
                    <option value="1.5,0.9">Compact (1.5m × 0.9m)</option>
                </select>
            </div>
            
            <div class="control-group">
                <label>Rotation (°)</label>
                <input type="range" id="rotation" min="0" max="359" value="0">
                <div class="range-value" id="rotation-value">0°</div>
            </div>
            
            <div class="control-group">
                <label>Puissance panneau (Wc)</label>
                <select id="panel-power">
                    <option value="400">400 Wc</option>
                    <option value="450" selected>450 Wc</option>
                    <option value="500">500 Wc</option>
                </select>
            </div>
            
            <h2>📋 Panneaux</h2>
            <div class="panel-list" id="panel-list">
                <div style="color: #666; text-align: center; padding: 20px;">
                    Cliquez sur l'image pour ajouter des panneaux
                </div>
            </div>
            
            <div class="help-text">
                💡 <strong>Astuce:</strong> Maintenez Shift pour placer plusieurs panneaux. 
                Cliquez sur un panneau pour le sélectionner et le supprimer.
            </div>
            
            <div class="logo">SOLAIRE FACILE</div>
        </div>
        
        <div class="main">
            <div class="toolbar">
                <button class="btn btn-primary" onclick="setMode('add')">➕ Ajouter</button>
                <button class="btn btn-secondary" onclick="setMode('select')">🖱️ Sélectionner</button>
                <button class="btn btn-danger" onclick="clearAllPanels()">🗑️ Tout effacer</button>
                <button class="btn btn-outline" onclick="undoLast()">↩️ Annuler</button>
                <button class="btn btn-primary" onclick="exportImage()">📷 Exporter</button>
                <button class="btn btn-secondary" onclick="exportData()">💾 JSON</button>
            </div>
            
            <div id="canvas-container">
                <canvas id="editor-canvas"></canvas>
                <div class="mode-indicator add" id="mode-indicator">Mode: Ajout</div>
                <div class="coords" id="coords">X: 0, Y: 0</div>
            </div>
        </div>
    </div>

    <script>
        // Configuration
        const CONFIG = {{
            lat: {lat},
            lon: {lon},
            metersPerPixel: 0.3,  // Approximation à zoom 19
            panelColor: 'rgba(30, 30, 80, 0.85)',
            panelBorder: '#4444ff',
            selectedColor: 'rgba(255, 100, 100, 0.85)',
            gridColor: 'rgba(255, 255, 255, 0.1)'
        }};
        
        // État
        let panels = [];
        let selectedPanel = null;
        let mode = 'add';
        let rotation = 0;
        let panelSize = [1.7, 1.0];  // mètres
        let panelPower = 450;  // Wc
        
        // Canvas setup
        const canvas = document.getElementById('editor-canvas');
        const ctx = canvas.getContext('2d');
        const bgImage = new Image();
        
        bgImage.onload = function() {{
            canvas.width = bgImage.width;
            canvas.height = bgImage.height;
            render();
        }};
        bgImage.src = 'data:image/jpeg;base64,{orthophoto_base64}';
        
        // Render
        function render() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Background
            ctx.drawImage(bgImage, 0, 0);
            
            // Grid (optional)
            // drawGrid();
            
            // Panels
            panels.forEach((panel, index) => {{
                drawPanel(panel, index === selectedPanel);
            }});
            
            updateStats();
        }}
        
        function drawPanel(panel, isSelected) {{
            const {{ x, y, rotation, width, height }} = panel;
            
            ctx.save();
            ctx.translate(x, y);
            ctx.rotate(rotation * Math.PI / 180);
            
            // Panel body
            ctx.fillStyle = isSelected ? CONFIG.selectedColor : CONFIG.panelColor;
            ctx.fillRect(-width/2, -height/2, width, height);
            
            // Border
            ctx.strokeStyle = isSelected ? '#ff4444' : CONFIG.panelBorder;
            ctx.lineWidth = isSelected ? 3 : 2;
            ctx.strokeRect(-width/2, -height/2, width, height);
            
            // Cell grid
            ctx.strokeStyle = 'rgba(100, 100, 150, 0.5)';
            ctx.lineWidth = 1;
            const cellsX = 6, cellsY = 10;
            for (let i = 1; i < cellsX; i++) {{
                const cx = -width/2 + (width / cellsX) * i;
                ctx.beginPath();
                ctx.moveTo(cx, -height/2);
                ctx.lineTo(cx, height/2);
                ctx.stroke();
            }}
            for (let i = 1; i < cellsY; i++) {{
                const cy = -height/2 + (height / cellsY) * i;
                ctx.beginPath();
                ctx.moveTo(-width/2, cy);
                ctx.lineTo(width/2, cy);
                ctx.stroke();
            }}
            
            // Frame highlight
            ctx.strokeStyle = 'rgba(200, 200, 220, 0.8)';
            ctx.lineWidth = 3;
            ctx.strokeRect(-width/2 + 2, -height/2 + 2, width - 4, height - 4);
            
            ctx.restore();
        }}
        
        function metersToPixels(meters) {{
            return meters / CONFIG.metersPerPixel;
        }}
        
        // Event handlers
        canvas.addEventListener('click', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (canvas.width / rect.width);
            const y = (e.clientY - rect.top) * (canvas.height / rect.height);
            
            if (mode === 'add') {{
                addPanel(x, y);
            }} else {{
                selectPanelAt(x, y);
            }}
        }});
        
        canvas.addEventListener('mousemove', (e) => {{
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) * (canvas.width / rect.width);
            const y = (e.clientY - rect.top) * (canvas.height / rect.height);
            
            document.getElementById('coords').textContent = 
                `X: ${{Math.round(x)}}, Y: ${{Math.round(y)}}`;
        }});
        
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Delete' && selectedPanel !== null) {{
                panels.splice(selectedPanel, 1);
                selectedPanel = null;
                render();
                updatePanelList();
            }}
            if (e.key === 'Escape') {{
                selectedPanel = null;
                render();
            }}
        }});
        
        // Panel management
        function addPanel(x, y) {{
            const widthPx = metersToPixels(panelSize[0]);
            const heightPx = metersToPixels(panelSize[1]);
            
            panels.push({{
                x: x,
                y: y,
                rotation: rotation,
                width: widthPx,
                height: heightPx,
                widthM: panelSize[0],
                heightM: panelSize[1],
                power: panelPower
            }});
            
            render();
            updatePanelList();
        }}
        
        function selectPanelAt(x, y) {{
            selectedPanel = null;
            
            for (let i = panels.length - 1; i >= 0; i--) {{
                const p = panels[i];
                const dx = x - p.x;
                const dy = y - p.y;
                
                // Simple bounding box check (could be improved for rotation)
                const maxDist = Math.max(p.width, p.height) / 2;
                if (Math.abs(dx) < maxDist && Math.abs(dy) < maxDist) {{
                    selectedPanel = i;
                    break;
                }}
            }}
            
            render();
        }}
        
        function deletePanel(index) {{
            panels.splice(index, 1);
            if (selectedPanel === index) selectedPanel = null;
            if (selectedPanel > index) selectedPanel--;
            render();
            updatePanelList();
        }}
        
        function clearAllPanels() {{
            if (confirm('Supprimer tous les panneaux ?')) {{
                panels = [];
                selectedPanel = null;
                render();
                updatePanelList();
            }}
        }}
        
        function undoLast() {{
            if (panels.length > 0) {{
                panels.pop();
                render();
                updatePanelList();
            }}
        }}
        
        // UI functions
        function setMode(newMode) {{
            mode = newMode;
            const indicator = document.getElementById('mode-indicator');
            indicator.textContent = mode === 'add' ? 'Mode: Ajout' : 'Mode: Sélection';
            indicator.className = 'mode-indicator ' + mode;
            canvas.style.cursor = mode === 'add' ? 'crosshair' : 'pointer';
        }}
        
        function updateStats() {{
            const count = panels.length;
            const totalPower = panels.reduce((sum, p) => sum + p.power, 0) / 1000;  // kWc
            const production = Math.round(totalPower * 1100);  // ~1100 kWh/kWc en France
            const surface = panels.reduce((sum, p) => sum + p.widthM * p.heightM, 0);
            
            document.getElementById('panel-count').textContent = count;
            document.getElementById('power').textContent = totalPower.toFixed(2) + ' kWc';
            document.getElementById('production').textContent = production + ' kWh/an';
            document.getElementById('surface').textContent = surface.toFixed(1) + ' m²';
        }}
        
        function updatePanelList() {{
            const list = document.getElementById('panel-list');
            
            if (panels.length === 0) {{
                list.innerHTML = '<div style="color: #666; text-align: center; padding: 20px;">Cliquez sur l\\'image pour ajouter des panneaux</div>';
                return;
            }}
            
            list.innerHTML = panels.map((p, i) => `
                <div class="panel-item">
                    <span>Panneau ${{i + 1}} (${{p.widthM}}×${{p.heightM}}m, ${{p.rotation}}°)</span>
                    <button class="delete-btn" onclick="deletePanel(${{i}})">✕</button>
                </div>
            `).join('');
        }}
        
        // Control handlers
        document.getElementById('rotation').addEventListener('input', (e) => {{
            rotation = parseInt(e.target.value);
            document.getElementById('rotation-value').textContent = rotation + '°';
        }});
        
        document.getElementById('panel-size').addEventListener('change', (e) => {{
            panelSize = e.target.value.split(',').map(Number);
        }});
        
        document.getElementById('panel-power').addEventListener('change', (e) => {{
            panelPower = parseInt(e.target.value);
        }});
        
        // Export functions
        function exportImage() {{
            const link = document.createElement('a');
            link.download = 'calepinage_solaire.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        }}
        
        function exportData() {{
            const data = {{
                location: {{ lat: CONFIG.lat, lon: CONFIG.lon }},
                panels: panels.map((p, i) => ({{
                    id: i + 1,
                    position: {{ x: p.x, y: p.y }},
                    rotation: p.rotation,
                    dimensions: {{ width: p.widthM, height: p.heightM }},
                    power: p.power
                }})),
                stats: {{
                    count: panels.length,
                    totalPowerKwc: panels.reduce((s, p) => s + p.power, 0) / 1000,
                    estimatedProductionKwh: Math.round(panels.reduce((s, p) => s + p.power, 0) / 1000 * 1100),
                    totalSurfaceM2: panels.reduce((s, p) => s + p.widthM * p.heightM, 0)
                }}
            }};
            
            const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: 'application/json' }});
            const link = document.createElement('a');
            link.download = 'calepinage_data.json';
            link.href = URL.createObjectURL(blob);
            link.click();
        }}
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def main():
    if len(sys.argv) < 3:
        print("=" * 60)
        print("ÉDITEUR DE CALEPINAGE SOLAIRE")
        print("=" * 60)
        print()
        print("Usage:")
        print("  python calepinage_editor.py <latitude> <longitude>")
        print()
        print("Exemple:")
        print("  python calepinage_editor.py 43.326370 5.394495")
        print()
        sys.exit(1)
    
    lat = float(sys.argv[1])
    lon = float(sys.argv[2])
    zoom = int(sys.argv[3]) if len(sys.argv) > 3 else 19
    
    print("=" * 60)
    print("ÉDITEUR DE CALEPINAGE SOLAIRE")
    print("=" * 60)
    print(f"Coordonnées: {lat}, {lon}")
    print(f"Zoom: {zoom}")
    print()
    
    # 1. Récupérer l'orthophoto
    print("[1/3] Récupération orthophoto...")
    try:
        ortho_img = get_orthophoto_composite(lat, lon, zoom=zoom, grid_size=3)
        
        # Convertir en base64
        buffer = BytesIO()
        ortho_img.save(buffer, format='JPEG', quality=90)
        ortho_base64 = base64.b64encode(buffer.getvalue()).decode()
        print(f"      ✓ Image {ortho_img.width}x{ortho_img.height}px")
    except Exception as e:
        print(f"      ✗ Erreur: {e}")
        # Créer une image placeholder
        ortho_img = Image.new('RGB', (768, 768), (100, 100, 100))
        buffer = BytesIO()
        ortho_img.save(buffer, format='JPEG')
        ortho_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # 2. Récupérer la parcelle
    print("[2/3] Récupération données cadastrales...")
    parcelle_data = get_parcelle_geometry(lat, lon)
    if parcelle_data and parcelle_data.get("success"):
        p = parcelle_data.get("parcelle", {})
        print(f"      ✓ Parcelle {p.get('section')}-{p.get('numero')}")
    else:
        print("      ⚠ Parcelle non trouvée")
        parcelle_data = None
    
    # 3. Générer l'éditeur HTML
    print("[3/3] Génération éditeur interactif...")
    output_path = f"calepinage_editor_{lat}_{lon}.html"
    generate_panel_editor_html(lat, lon, ortho_base64, parcelle_data, output_path)
    print(f"      ✓ Fichier: {output_path}")
    
    print()
    print("=" * 60)
    print("TERMINÉ!")
    print("=" * 60)
    print(f"Ouvrez '{output_path}' dans votre navigateur")
    print()
    print("Instructions:")
    print("  - Cliquez pour placer des panneaux")
    print("  - Ajustez la rotation et la taille")
    print("  - Exportez l'image ou les données JSON")


if __name__ == "__main__":
    main()
