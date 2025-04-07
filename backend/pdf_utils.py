# backend/pdf_utils.py

import fitz  # PyMuPDF

def extract_text_slides(pdf_path: str) -> list[str]:
    """
    Extrait le texte de chaque page du PDF comme une slide.
    Ignore les pages vides.
    """
    slides = []
    with fitz.open(pdf_path) as doc:
        for idx, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                slides.append(text)
            else:
                print(f"⚠️ Slide vide détectée à la page {idx}, ignorée.")
    return slides
