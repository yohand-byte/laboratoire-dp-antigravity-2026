"""
Générateur de PDF pour les dossiers de Déclaration Préalable (DP)
Version optimisée pour le DP Generator Lab
"""
import os
import math
import tempfile
import logging
import hashlib
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from PIL import Image

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm, cm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont

# Dimensions A4 paysage
PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)
MARGIN = 15 * mm

def detect_image_suffix(content: bytes) -> str:
    """Détecte une extension probable (jpg/png) à partir des magic bytes."""
    if not content:
        return ".img"
    if content.startswith(b"\xff\xd8"):
        return ".jpg"
    if content.startswith(b"\x89PNG"):
        return ".png"
    return ".img"

class DPColors:
    """Couleurs utilisées dans le document"""
    PRIMARY_BLUE = HexColor('#003366')
    ACCENT_ORANGE = HexColor('#FFA500')
    PANEL_GRAY = HexColor('#50506E')
    ROOF_GREEN = HexColor('#90EE90')
    OBSTACLE_ORANGE = HexColor('#FF8C00')
    BORDER_RED = HexColor('#DC3545')
    TEXT_DARK = HexColor('#212529')
    WHITE = HexColor('#FFFFFF')
    BLACK = HexColor('#000000')
    LIGHT_GRAY = HexColor('#F0F0F0')


class PDFGenerator:
    """Générateur de PDF pour les dossiers DP Mairie"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.c = canvas.Canvas(output_path, pagesize=landscape(A4))
        self.width = PAGE_WIDTH
        self.height = PAGE_HEIGHT
        
    def draw_footer(self, company_name: str, scale: str, title: str, logo_path: str = None):
        """Dessine le footer standardisé sur la page courante"""
        footer_height = 12 * mm
        footer_y = MARGIN
        
        # Bordure du footer
        self.c.setStrokeColor(black)
        self.c.setLineWidth(1)
        self.c.rect(MARGIN, footer_y, self.width - 2 * MARGIN, footer_height)
        
        # Séparateurs verticaux (3 colonnes)
        col_width = (self.width - 2 * MARGIN) / 3
        self.c.line(MARGIN + col_width, footer_y, MARGIN + col_width, footer_y + footer_height)
        self.c.line(MARGIN + 2 * col_width, footer_y, MARGIN + 2 * col_width, footer_y + footer_height)
        
        # Textes
        self.c.setFont("Helvetica-Bold", 10)
        
        # Colonne 1: Société/Logo
        if logo_path and os.path.exists(logo_path):
            try:
                self.c.drawImage(logo_path, MARGIN + 5, footer_y + 2, 
                               width=col_width - 10, height=footer_height - 4,
                               preserveAspectRatio=True)
            except:
                self.c.setFillColor(DPColors.PRIMARY_BLUE)
                self.c.drawCentredString(MARGIN + col_width / 2, footer_y + 4, company_name)
        else:
            self.c.setFillColor(DPColors.PRIMARY_BLUE)
            self.c.drawCentredString(MARGIN + col_width / 2, footer_y + 4, company_name)
        
        # Colonne 2: Échelle
        self.c.setFillColor(black)
        self.c.drawCentredString(MARGIN + col_width + col_width / 2, footer_y + 4, f"Ech : {scale}")
        
        # Colonne 3: Titre
        self.c.drawCentredString(MARGIN + 2 * col_width + col_width / 2, footer_y + 4, title)
    
    def draw_compass(self, x: float, y: float, size: float = 60, 
                     with_azimuth: bool = False, azimuth: float = 0):
        """Dessine une rose des vents"""
        self.c.saveState()
        
        center_x = x + size / 2
        center_y = y + size / 2
        radius = size / 2 - 5
        
        # Cercle extérieur
        self.c.setStrokeColor(HexColor('#333333'))
        self.c.setLineWidth(1.5)
        self.c.circle(center_x, center_y, radius)
        
        # Branches principales
        self.c.setFillColor(HexColor('#333333'))
        
        # Nord (triangle rouge)
        self.c.setFillColor(HexColor('#B00000'))
        north_path = self.c.beginPath()
        north_path.moveTo(center_x, center_y + radius - 5)
        north_path.lineTo(center_x - 6, center_y)
        north_path.lineTo(center_x + 6, center_y)
        north_path.close()
        self.c.drawPath(north_path, fill=1)
        
        # Sud
        self.c.setFillColor(HexColor('#333333'))
        south_path = self.c.beginPath()
        south_path.moveTo(center_x, center_y - radius + 5)
        south_path.lineTo(center_x - 6, center_y)
        south_path.lineTo(center_x + 6, center_y)
        south_path.close()
        self.c.drawPath(south_path, fill=1)
        
        # Est
        east_path = self.c.beginPath()
        east_path.moveTo(center_x + radius - 5, center_y)
        east_path.lineTo(center_x, center_y - 6)
        east_path.lineTo(center_x, center_y + 6)
        east_path.close()
        self.c.drawPath(east_path, fill=1)
        
        # Ouest
        west_path = self.c.beginPath()
        west_path.moveTo(center_x - radius + 5, center_y)
        west_path.lineTo(center_x, center_y - 6)
        west_path.lineTo(center_x, center_y + 6)
        west_path.close()
        self.c.drawPath(west_path, fill=1)
        
        # Labels
        self.c.setFont("Helvetica-Bold", 8)
        self.c.setFillColor(HexColor('#333333'))
        self.c.drawCentredString(center_x, center_y + radius + 3, "N")
        self.c.drawCentredString(center_x, center_y - radius - 10, "S")
        self.c.drawCentredString(center_x + radius + 8, center_y - 3, "E")
        self.c.drawCentredString(center_x - radius - 8, center_y - 3, "O")
        
        # Ligne d'azimuth si demandé
        if with_azimuth and azimuth != 0:
            self.c.setStrokeColor(DPColors.BORDER_RED)
            self.c.setLineWidth(2)
            angle_rad = math.radians(90 - azimuth)  # Convertir en radians depuis le Nord
            end_x = center_x + (radius + 10) * math.cos(angle_rad)
            end_y = center_y + (radius + 10) * math.sin(angle_rad)
            self.c.line(center_x, center_y, end_x, end_y)
            
            # Label de l'angle
            self.c.setFont("Helvetica", 7)
            self.c.setFillColor(DPColors.BORDER_RED)
            self.c.drawString(end_x + 3, end_y, f"{int(azimuth)}°")
        
        # Point central
        self.c.setFillColor(HexColor('#333333'))
        self.c.circle(center_x, center_y, 3, fill=1)
        
        self.c.restoreState()
    
    def draw_legend_box(self, x: float, y: float, width: float, 
                        items: List[Tuple[str, str]], title: str = "Légende supplémentaire:"):
        """Dessine une boîte de légende"""
        item_height = 6 * mm
        padding = 3 * mm
        total_height = padding + 5 * mm + len(items) * item_height + padding
        
        # Fond et bordure
        self.c.setFillColor(white)
        self.c.setStrokeColor(black)
        self.c.rect(x, y - total_height, width, total_height, fill=1, stroke=1)
        
        # Titre
        self.c.setFont("Helvetica-Bold", 8)
        self.c.setFillColor(black)
        self.c.drawString(x + padding, y - padding - 4 * mm, title)
        
        # Items
        self.c.setFont("Helvetica", 7)
        current_y = y - padding - 5 * mm - item_height
        
        for label, color_hex in items:
            # Rectangle de couleur
            self.c.setFillColor(HexColor(color_hex))
            self.c.rect(x + padding, current_y, 5 * mm, 4 * mm, fill=1, stroke=1)
            
            # Texte
            self.c.setFillColor(black)
            self.c.drawString(x + padding + 7 * mm, current_y + 1 * mm, label)
            
            current_y -= item_height
    
    def add_image_to_page(self, image_bytes: bytes, x: float, y: float,
                          width: float, height: float, border: bool = True,
                          placeholder_text: str = None, name: str = "unknown",
                          strict: bool = False):
        """Ajoute une image sur la page, sinon un placeholder lisible."""
        if not image_bytes:
            if strict:
                raise ValueError(f"missing/invalid {name}")
            self.c.setFillColor(HexColor('#E0E0E0'))
            self.c.rect(x, y, width, height, fill=1, stroke=0)
            self.c.setFillColor(HexColor('#666666'))
            self.c.setFont("Helvetica", 12)
            text = placeholder_text or "Image non disponible"
            self.c.drawCentredString(x + width / 2, y + height / 2, text)
        else:
            suffix = detect_image_suffix(image_bytes)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            try:
                self.c.drawImage(tmp_path, x, y, width=width, height=height,
                                 preserveAspectRatio=True)
            except Exception as e:
                logging.error(f"Error drawing image {name}: {e}")
                if strict: raise e
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        if border:
            self.c.setStrokeColor(black)
            self.c.setLineWidth(0.5)
            self.c.rect(x, y, width, height)
    
    def add_image_contain(self, image_bytes: bytes, x: float, y: float,
                          width: float, height: float, caption: Optional[str] = None,
                          return_box: bool = False, name: str = "unknown",
                          strict: bool = False):
        """Ajoute une image en mode 'contain' centré."""
        if not image_bytes:
            if strict: raise ValueError(f"missing/invalid {name}")
            self.c.setStrokeColor(black)
            self.c.setLineWidth(0.5)
            self.c.rect(x, y, width, height)
            return None
        
        suffix = detect_image_suffix(image_bytes)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name
        
        try:
            with Image.open(tmp_path) as img:
                img_w, img_h = img.size
            scale = min(width / img_w, height / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale
            draw_x = x + (width - draw_w) / 2
            draw_y = y + (height - draw_h) / 2
            self.c.drawImage(tmp_path, draw_x, draw_y, width=draw_w, height=draw_h, preserveAspectRatio=False)
            
            # Cadre
            self.c.setStrokeColor(black)
            self.c.setLineWidth(0.5)
            self.c.rect(x, y, width, height)
            
            if caption:
                self.c.setFillColor(HexColor('#f5f5f5'))
                self.c.rect(x, y, width, 12, fill=1, stroke=0)
                self.c.setFillColor(HexColor('#666666'))
                self.c.setFont("Helvetica", 8)
                self.c.drawString(x + 4, y + 3, caption)
                
            if return_box:
                return (draw_x, draw_y, draw_w, draw_h)
        except Exception as e:
            logging.error(f"Error drawing image {name}: {e}")
            if strict: raise e
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        return None

    # PAGES
    def create_page_garde(self, data: Dict[str, Any], image_3d: bytes = None):
        self.c.setFillColor(white)
        self.c.rect(0, 0, self.width, self.height, fill=1)
        gutter = 12 * mm
        col_left_w = (self.width - 2 * MARGIN - gutter) * 0.52
        col_right_w = (self.width - 2 * MARGIN - gutter) * 0.48
        left_x = MARGIN
        right_x = MARGIN + col_left_w + gutter
        img_h, img_w = self.height * 0.58, col_left_w
        img_y, bar_h = self.height - MARGIN - img_h, 22 * mm
        self.c.setFillColor(DPColors.PRIMARY_BLUE); self.c.rect(left_x, img_y + img_h - bar_h, img_w, bar_h, fill=1, stroke=0)
        self.c.setFillColor(white); self.c.setFont("Helvetica-Bold", 18); self.c.drawCentredString(left_x + img_w / 2, img_y + img_h - bar_h / 2 - 2, "DÉCLARATION PRÉALABLE")
        if image_3d: self.add_image_contain(image_3d, left_x, img_y, img_w, img_h - bar_h)
        # Liste des pièces corrigée selon standard
        pieces = [
            ("DP1 :", "Plan de situation"),
            ("DP2 :", "Plan de masse"),
            ("DP4 :", "Calpinage"),
            ("DP5 :", "Visualisation 3D"),
            ("DP6 :", "Insertion du projet"),
            ("DP7 :", "Terrain vue de près"),
            ("DP8 :", "Terrain vue de loin"),
            ("DP11 :", "Note architecturale")
        ]
        
        self.c.setFillColor(black)
        list_y = img_y - 9 * mm
        
        for code, label in pieces:
            # Code en gras
            self.c.setFont("Helvetica-Bold", 10)
            self.c.drawString(left_x, list_y, code)
            
            # Label en dessous (selon extraction PDF référence) ou à côté ?
            # L'extraction montre "DP1 : \n Plan de situation", donc peut-être en dessous ou décalé.
            # Le screenshot standard montrait une liste alignée. Gardons aligné mais avec les bons textes.
            self.c.setFont("Helvetica", 10)
            self.c.drawString(left_x + 35, list_y, label)
            list_y -= 6 * mm
            
        # Ajout "DOSSIER REALISE PAR" en bas à droite
        self.c.setFont("Helvetica-Bold", 8)
        self.c.setFillColor(DPColors.PRIMARY_BLUE)
        self.c.drawCentredString(right_x + col_right_w / 2, 20 * mm, "DOSSIER REALISE PAR")
        
        # Logo (variable) ou nom société (variable) en dessous
        logo_path = data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            # Dessiner le logo centré
            lb_x = right_x + col_right_w / 2 - 20 * mm
            lb_y = 5 * mm
            lb_w = 40 * mm
            lb_h = 12 * mm
            try:
                self.c.drawImage(logo_path, lb_x, lb_y, width=lb_w, height=lb_h, preserveAspectRatio=True, mask='auto')
            except Exception as e:
                logging.error(f"Error drawing logo on cover: {e}")
                self.c.setFillColor(black)
                self.c.drawCentredString(right_x + col_right_w / 2, 15 * mm, data.get('societe', 'SOLAIRE FACILE'))
        else:
            self.c.setFillColor(black)
            self.c.drawCentredString(right_x + col_right_w / 2, 15 * mm, data.get('societe', 'SOLAIRE FACILE'))
        current_y = self.height - MARGIN - 28 * mm
        def draw_block(title, lines):
            nonlocal current_y
            block_h = 28 * mm
            # Fond bleu
            self.c.setFillColor(DPColors.PRIMARY_BLUE)
            self.c.rect(right_x, current_y, col_right_w, block_h, fill=1, stroke=0)
            
            # Calcul hauteur contenu pour centrage vertical
            # Titre: ~11pt, Espace: 4pt, Lignes: ~10pt + espace 2pt
            title_h = 11
            line_h = 10
            line_spacing = 2
            content_h = title_h + 4 + len(lines) * (line_h + line_spacing) - line_spacing
            
            # Start Y (depuis le haut du bloc)
            top_padding = (block_h/mm * 2.83465 - content_h) / 2 # conversion mm->pt
            
            # Dessin Titre
            self.c.setFillColor(white)
            self.c.setFont("Helvetica-Bold", 11)
            # Y position en pt depuis le bas de la page
            # current_y est le bas du rectangle
            # On veut dessiner par rapport au haut du rectangle (current_y + block_h)
            draw_y = current_y + block_h - (top_padding * mm / 2.83465) - 8 # Ajustement empirique retour mm
            
            self.c.drawCentredString(right_x + col_right_w / 2, draw_y, title)
            
            # Dessin Lignes
            self.c.setFont("Helvetica-Bold", 10)
            draw_y -= (14) # Espace sous titre
            
            for l in lines:
                self.c.drawCentredString(right_x + col_right_w / 2, draw_y, l)
                draw_y -= 12
                
            current_y -= (block_h + 8*mm)
        draw_block("PROJET", ["Pose de panneaux photovoltaïques"])
        draw_block("MAÎTRE D'OUVRAGE", [data.get("maitre_ouvrage", "")])
        draw_block("ADRESSE DU PROJET", [data.get("adresse", ""), f"{data.get('cp','')} {data.get('ville','')}".strip()])
        self.c.showPage()

    def create_page_dp1_1000(self, data: Dict[str, Any], cadastre_image: bytes = None, aerial_image: bytes = None):
        h = self.height - 2*MARGIN - 15*mm; y = MARGIN + 15*mm; cad_w = (self.width - 3*MARGIN)/2; cad_h = h - 20*mm
        self.c.setFont("Helvetica-Bold", 12); self.c.drawString(MARGIN, self.height - MARGIN - 10, f"Parcelle {data.get('parcelle', '')}")
        self.add_image_to_page(cadastre_image, MARGIN, y, cad_w, cad_h, name="cad1000")
        self.add_image_to_page(aerial_image, MARGIN + cad_w + MARGIN, y, cad_w, cad_h, name="aer1000")
        self.draw_compass(self.width - MARGIN - 70, self.height - MARGIN - 80, 60)
        self.draw_footer(data.get('societe', ''), "1/1000", "DP1 : PLAN DE SITUATION", data.get('logo_path'))
        self.c.showPage()

    def create_page_dp4(self, data: Dict[str, Any], roof_image: bytes = None):
        y_table = self.height - MARGIN - 40*mm
        self.c.setFont("Helvetica-Bold", 12); self.c.drawCentredString(self.width/2, self.height - MARGIN - 10, "DP4 : CALEPINAGE")
        if roof_image: 
            self.add_image_contain(roof_image, MARGIN, MARGIN + 20*mm, self.width - 2*MARGIN, y_table - MARGIN - 25*mm)
        self.draw_compass(self.width - MARGIN - 70, MARGIN + 30*mm, 60, with_azimuth=True, azimuth=data.get('azimuth', 180))
        self.draw_footer(data.get('societe', ''), "1/---", "DP4 : CALEPINAGE")
        self.c.showPage()

    def save(self):
        self.c.save()

def generate_complete_dp(data: Dict[str, Any], images: Dict[str, bytes], output_path: str) -> str:
    pdf = PDFGenerator(output_path)
    pdf.create_page_garde(data, images.get('3d'))
    pdf.create_page_dp1_1000(data, images.get('cadastre_1000'), images.get('aerial_1000'))
    pdf.create_page_dp4(data, images.get('calepinage'))
    pdf.save()
    return output_path
