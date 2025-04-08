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
    include_intuition: bool = False,
    include_retenir: bool = False,
    include_vulgarisation: bool = False,
    include_recap: bool = False,
    box_styles: dict = None,
    vulgarization_level: int = 0
) -> str:
    slides = extract_text_slides(pdf_path)
    print(f"Nombre de slides extraites : {len(slides)}")
    print(f"Langue source : {source_language}")
    print(f"Langue cible : {target_language}")
    print(f"Inclure intuition : {include_intuition}")
    print(f"Inclure à retenir : {include_retenir}")
    print(f"Inclure vulgarisation : {include_vulgarisation}")
    print(f"Inclure fiche récap : {include_recap}")
    print(f"Niveau de vulgarisation : {vulgarization_level}")
    print(f"Styles des boîtes : {box_styles}")
    
    context = CourseContext(course_title)
    latex_parts = [f"% Cours : {course_title}"]
    current_chapter = None
    chapter_content = []

    for idx, slide in enumerate(slides, 1):
        print(f"\n[Slide {idx}/{len(slides)}] Analyse en cours...")
        print(f"Contenu de la slide :\n{slide[:200]}...")  # Affiche les 200 premiers caractères
        
        # Détecter si c'est un nouveau chapitre
        if slide.startswith(("Chapitre", "Chapter", "Partie", "Part")) or idx == 1:
            if current_chapter and chapter_content and include_recap:
                # Générer la fiche récapitulative du chapitre précédent
                recap_prompt = f"""
Génère une fiche récapitulative pour le chapitre suivant :
{current_chapter}

Contenu du chapitre :
{" ".join(chapter_content)}

La fiche doit inclure :
1. Les points clés
2. Les formules importantes
3. Les concepts essentiels
4. Les applications pratiques

Format : Utilise le même format que les autres blocs avec tcolorbox.
"""
                recap_result = analyze_slide(
                    recap_prompt,
                    context,
                    source_language=source_language,
                    target_language=target_language,
                    include_intuition=include_intuition,
                    include_retenir=include_retenir,
                    include_vulgarisation=include_vulgarisation,
                    include_recap=include_recap,
                    box_styles=box_styles,
                    vulgarization_level=vulgarization_level
                )
                if recap_result["content"]:
                    latex_parts.append("\n\\section*{Fiche Récapitulative}")
                    latex_parts.append(recap_result["content"])
            
            current_chapter = slide.split("\n")[0]
            chapter_content = []
        
        result = analyze_slide(
            slide, 
            context, 
            source_language=source_language,
            target_language=target_language,
            include_intuition=include_intuition,
            include_retenir=include_retenir,
            include_vulgarisation=include_vulgarisation,
            include_recap=include_recap,
            box_styles=box_styles,
            vulgarization_level=vulgarization_level
        )

        # On ajoute les blocs dans l'ordre souhaité
        if include_intuition and result["intuition"]:
            latex_parts.append(result["intuition"])
        if include_vulgarisation and result["vulgarisation"]:
            latex_parts.append(result["vulgarisation"])
        if result["content"]:
            latex_parts.append(result["content"])
            chapter_content.append(result["content"])
        if result["algorithm"]:
            latex_parts.append(result["algorithm"])
        if include_retenir and result["aretenir"]:
            latex_parts.append(result["aretenir"])

        latex_parts.append("")  # Saut de ligne pour séparer les slides

    # Générer la fiche récapitulative du dernier chapitre
    if current_chapter and chapter_content and include_recap:
        recap_prompt = f"""
Génère une fiche récapitulative pour le chapitre suivant :
{current_chapter}

Contenu du chapitre :
{" ".join(chapter_content)}

La fiche doit inclure :
1. Les points clés
2. Les formules importantes
3. Les concepts essentiels
4. Les applications pratiques

Format : Utilise le même format que les autres blocs avec tcolorbox.
"""
        recap_result = analyze_slide(
            recap_prompt,
            context,
            source_language=source_language,
            target_language=target_language,
            include_intuition=include_intuition,
            include_retenir=include_retenir,
            include_vulgarisation=include_vulgarisation,
            include_recap=include_recap,
            box_styles=box_styles,
            vulgarization_level=vulgarization_level
        )
        if recap_result["content"]:
            latex_parts.append("\n\\section*{Fiche Récapitulative}")
            latex_parts.append(recap_result["content"])

    full_latex_body = "\n".join(latex_parts)
    return build_latex_document(full_latex_body, course_title, target_language)
