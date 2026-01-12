import sys
import os
sys.path.append(os.path.abspath("dp-generator-lab"))

from modules.pdf_generator import PDFGenerator, DPColors
from PIL import Image, ImageDraw
from io import BytesIO

# Output file
output_path = "artifacts/dp1_preview.pdf"

# Instantiate generator
pdf = PDFGenerator(output_path)

# Mock Data
data = {
    "maitre_ouvrage": "M. TEST",
    "adresse": "123 Rue de Test",
    "cp": "75000",
    "ville": "VILLE",
    "societe": "SOLAIRE FACILE",
    "parcelle": "0001 - Section A",
    "logo_path": "artifacts/dummy_logo.png" # Existing dummy logo
}

# Create unrealistic but explicit Cadastre Image
cad_img = Image.new('RGB', (800, 600), color = 'white')
d = ImageDraw.Draw(cad_img)
# Draw some random polygons to simulate parcels
points1 = [(100, 100), (300, 50), (400, 200), (200, 300)]
points2 = [(400, 200), (600, 150), (700, 400), (300, 500)]
d.polygon(points1, outline="black", width=2)
d.polygon(points2, outline="black", width=2)
# Highlight one in red (selected parcel)
d.polygon(points1, outline="red", width=5)
# Add some text
d.text((120, 120), "PARCELLE 123 (Cible)", fill="red")
cad_bytes = BytesIO()
cad_img.save(cad_bytes, format='PNG')

# Create dummy Orthophoto (Satellite style)
aer_img = Image.new('RGB', (800, 600), color = '#2F4F4F') # Dark slate gray
d = ImageDraw.Draw(aer_img)
# Add some noise/texture visually
for i in range(0, 800, 50):
    d.line([(i, 0), (i, 600)], fill='#556B2F', width=2) # Olive
    d.line([(0, i), (800, i)], fill='#556B2F', width=2)
d.text((350, 280), "ORTHOPHOTO IGN", fill="white")
# Simulate overlay of red parcel on ortho
d.polygon(points1, outline="red", width=3)
aer_bytes = BytesIO()
aer_img.save(aer_bytes, format='JPEG')

print("Generating DP1...")
pdf.create_page_dp1_1000(data, cadastre_image=cad_bytes.getvalue(), aerial_image=aer_bytes.getvalue())
pdf.save()
print(f"PDF Generated at {output_path}")
