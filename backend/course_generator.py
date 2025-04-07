# backend/course_generator.py

from backend.pdf_utils import extract_text_slides
from backend.context import CourseContext
from backend.analyzer import analyze_slide
from backend.latex_builder import build_latex_document

def generate_course_latex(
    pdf_path: str, 
    course_title: str, 
    source_language: str = "french",
    target_language: str = "french",
    vulgarization_level: int = 0
) -> str:
    slides = extract_text_slides(pdf_path)
    print(f"Nombre de slides extraites : {len(slides)}")
    print(f"Langue source : {source_language}")
    print(f"Langue cible : {target_language}")
    print(f"Niveau de vulgarisation : {vulgarization_level}")
    
    context = CourseContext(course_title)
    latex_parts = [f"% Cours : {course_title}"]

    for idx, slide in enumerate(slides, 1):
        print(f"\n[Slide {idx}/{len(slides)}] Analyse en cours...")
        print(f"Contenu de la slide :\n{slide[:200]}...")  # Affiche les 200 premiers caractères
        
        result = analyze_slide(
            slide, 
            context, 
            source_language=source_language,
            target_language=target_language,
            vulgarization_level=vulgarization_level
        )

        # On ajoute directement les blocs retournés par GPT
        if result["content"]:
            latex_parts.append(result["content"])
        if result["algorithm"]:
            latex_parts.append(result["algorithm"])
        if result["aretenir"]:
            latex_parts.append(result["aretenir"])
        if result["intuition"]:
            latex_parts.append(result["intuition"])
        if vulgarization_level > 0 and result["vulgarisation"]:
            latex_parts.append(result["vulgarisation"])

        latex_parts.append("")  # Saut de ligne pour séparer les slides

    full_latex_body = "\n".join(latex_parts)
    return build_latex_document(full_latex_body, course_title, target_language)
