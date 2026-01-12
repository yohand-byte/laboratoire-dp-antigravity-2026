import sys
import os
sys.path.append(os.path.abspath("dp-generator-lab"))
from pypdf import PdfReader

def analyze_reference(path):
    reader = PdfReader(path)
    page = reader.pages[0]
    text = page.extract_text()
    print("--- TEXT CONTENT ---")
    print(text)
    print("--------------------")
    
    # Try to get image info if possible (basic)
    print(f"MediaBox: {page.mediabox}")

if __name__ == "__main__":
    analyze_reference("dp-generator-lab/assets/dp_reference.pdf")
