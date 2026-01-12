import sys
import os
# Add the project root to the python path to import modules
sys.path.append(os.path.abspath("dp-generator-lab"))

from modules.pdf_generator import PDFGenerator, generate_complete_dp
from PIL import Image
from io import BytesIO

# Output file
output_path = "artifacts/cover_page_preview.pdf"
os.makedirs("artifacts", exist_ok=True)

# Instantiate generator
pdf = PDFGenerator(output_path)

# Mock Data with Dummy Logo
logo_path = "artifacts/dummy_logo.png"
img_logo = Image.new('RGB', (200, 60), color = '#ff9933') # Orange logo
# Save dummy logo
out_logo = BytesIO()
img_logo.save("artifacts/dummy_logo.png", format='PNG')

data = {
    "maitre_ouvrage": "VARIABLE: M. NOM Prénom",
    "adresse": "VAR: 123 Rue de l'Exemple",
    "cp": "75000",
    "ville": "VILLE TEST",
    "societe": "VAR: INSTALLATEUR TEST",
    "logo_path": "artifacts/dummy_logo.png"
}

# Create a dummy 3D image for the visualization placeholder
img = Image.new('RGB', (800, 600), color = '#ffcccb') # Light red background
# Add some text to the image if possible (oops, PIL default font might be missing, keep simple)
from reportlab.lib.utils import ImageReader

# Convert PIL image to bytes
img_byte_arr = BytesIO()
img.save(img_byte_arr, format='PNG')
img_bytes = img_byte_arr.getvalue()

# Generate Page de Garde
print("Generating cover page...")
pdf.create_page_garde(data, image_3d=img_bytes)
pdf.save()

print(f"PDF Generated at {output_path}")
