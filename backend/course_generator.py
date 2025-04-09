# backend/course_generator.py

from backend.analyzer import convert_pdf_to_latex
from backend.latex_builder import build_latex_document

def generate_course_latex(
    pdf_path: str, 
    latex_path: str,
    course_title: str = None,
    source_lang: str = "french",
    target_lang: str = "french",
    include_intuition: bool = False,
    include_retenir: bool = False,
    include_vulgarisation: bool = False,
    include_recap: bool = False,
    box_styles: dict = None,
    box_options: dict = None,
    vulgarization_level: int = 0,
    model: str = "gpt-4",
    temperature: float = 0.2,
    use_all_packages: bool = True
) -> str:
    """
    Génère un document LaTeX à partir d'un PDF en utilisant GPT-4 Vision directement.
    
    Args:
        pdf_path: Chemin vers le fichier PDF source
        latex_path: Chemin où sauvegarder le fichier LaTeX généré
        course_title: Titre du cours (optionnel)
        source_lang: Langue source du document
        target_lang: Langue cible pour la traduction
        include_intuition: Inclure les boîtes d'intuition
        include_retenir: Inclure les boîtes "À retenir"
        include_vulgarisation: Inclure les boîtes de vulgarisation
        include_recap: Inclure les fiches récapitulatives
        box_styles: Styles des boîtes (couleurs)
        box_options: Options détaillées pour chaque type de boîte
        vulgarization_level: Niveau de vulgarisation (0-5)
        model: Modèle GPT à utiliser pour l'analyse
        temperature: Température pour la génération de texte
        use_all_packages: Utiliser tous les packages du fichier packages.txt
        
    Returns:
        str: Contenu LaTeX généré
    """
    print(f"Langue source : {source_lang}")
    print(f"Langue cible : {target_lang}")
    print(f"Inclure intuition : {include_intuition}")
    print(f"Inclure à retenir : {include_retenir}")
    print(f"Inclure vulgarisation : {include_vulgarisation}")
    print(f"Inclure fiche récap : {include_recap}")
    print(f"Niveau de vulgarisation : {vulgarization_level}")
    print(f"Styles des boîtes : {box_styles}")
    print(f"Options des boîtes : {box_options}")
    print(f"Modèle utilisé : {model}")
    print(f"Utiliser tous les packages : {use_all_packages}")
    
    # Déterminer quel modèle utiliser pour la vision
    vision_model = "gpt-4o"
    
    print(f"Conversion directe du PDF en LaTeX avec {vision_model}")
    
    # Convertir directement le PDF en LaTeX complet
    latex_body = convert_pdf_to_latex(
        pdf_path,
        course_title=course_title,
        target_language=target_lang,
        include_intuition=include_intuition,
        include_retenir=include_retenir,
        include_vulgarisation=include_vulgarisation,
        include_recap=include_recap,
        box_styles=box_styles,
        box_options=box_options,
        vulgarization_level=vulgarization_level,
        model=vision_model,
        temperature=temperature
    )
    
    # Extraire les configurations de boîtes tcolorbox
    tcolorbox_setup = ""
    if include_intuition or include_retenir or include_vulgarisation or include_recap:
        import re
        tcolorbox_pattern = r'\\NewTColorBox.*?}}}}'
        tcolorbox_matches = re.findall(tcolorbox_pattern, latex_body, re.DOTALL)
        
        if tcolorbox_matches:
            # Extraire la configuration des boîtes et la supprimer du corps du document
            for match in tcolorbox_matches:
                tcolorbox_setup += match + "\n\n"
                latex_body = latex_body.replace(match, "")
            
            # Nettoyer le corps du document
            latex_body = re.sub(r'\n{3,}', '\n\n', latex_body)
    
    # Construire le document LaTeX complet avec le préambule
    return build_latex_document(latex_body, course_title, target_lang, use_all_packages, box_setup=tcolorbox_setup)
