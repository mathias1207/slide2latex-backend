# backend/analyzer.py

import os
from dotenv import load_dotenv
load_dotenv()
import json
import re
import base64
from langdetect import detect, DetectorFactory
from openai import OpenAI
from backend.context import CourseContext
import fitz  # PyMuPDF pour la conversion de PDF en images
from PIL import Image
import io
import tempfile

# Pour rendre la détection de langue plus cohérente
DetectorFactory.seed = 0

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Constante pour échapper les backslashes
BACKSLASH = "\\"

def detect_language(text: str) -> str:
    """Détecte la langue d'un texte."""
    try:
        return detect(text)
    except:
        return "en"  # Langue par défaut si la détection échoue

def convert_pdf_pages_to_images(pdf_path: str, max_pages: int = 30) -> list:
    """
    Convertit les pages d'un PDF en images.
    
    Args:
        pdf_path: Chemin vers le fichier PDF à convertir
        max_pages: Nombre maximum de pages à convertir
        
    Returns:
        list: Liste des images encodées en base64
    """
    print(f"Conversion du PDF en images: {pdf_path}")
    images = []
    
    try:
        pdf_document = fitz.open(pdf_path)
        num_pages = min(len(pdf_document), max_pages)
        
        for page_num in range(num_pages):
            page = pdf_document.load_page(page_num)
            
            # Augmenter la résolution pour une meilleure qualité
            zoom = 2  # Zoom x 2 (meilleure qualité)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convertir le pixmap en image PIL
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Réduire la taille si nécessaire (compression)
            max_size = (1500, 1500)  # Taille maximale
            img.thumbnail(max_size, Image.LANCZOS)
            
            # Convertir en base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            images.append(img_base64)
            print(f"Page {page_num+1}/{num_pages} convertie")
        
        return images
        
    except Exception as e:
        print(f"Erreur lors de la conversion du PDF en images: {str(e)}")
        return []

def convert_pdf_to_latex(
    pdf_path: str,
    course_title: str = None,
    target_language: str = "french",
    include_intuition: bool = False,
    include_retenir: bool = False,
    include_vulgarisation: bool = False,
    include_recap: bool = False,
    box_styles: dict = None,
    box_options: dict = None,
    vulgarization_level: int = 0,
    model: str = "gpt-4o",
    temperature: float = 0.2
) -> str:
    """
    Convertit directement un fichier PDF en LaTeX en l'envoyant à GPT.
    
    Args:
        pdf_path: Chemin vers le fichier PDF source
        course_title: Titre du cours
        target_language: Langue cible pour le document LaTeX
        include_intuition: Inclure les boîtes d'intuition
        include_retenir: Inclure les boîtes "À retenir"
        include_vulgarisation: Inclure les boîtes de vulgarisation
        include_recap: Inclure les fiches récapitulatives
        box_styles: Styles des boîtes (couleurs)
        box_options: Options détaillées pour chaque type de boîte
        vulgarization_level: Niveau de vulgarisation (0-5)
        model: Modèle GPT à utiliser
        temperature: Température pour la génération de texte
        
    Returns:
        str: Contenu LaTeX complet
    """
    # Styles par défaut si non spécifiés
    if box_styles is None:
        box_styles = {
            "intuition": "green",
            "retenir": "yellow",
            "vulgarisation": "blue",
            "recap": "purple"
        }
    
    # Options de boîtes par défaut si non spécifiées
    if box_options is None:
        box_options = {
            "retenir": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faBookmark",
                "border": "boxrule=1pt",
                "background": ""
            },
            "intuition": {
                "titleFont": "lmr",
                "contentFont": "lmr", 
                "icon": "\\faLightbulb",
                "border": "boxrule=1pt",
                "background": ""
            },
            "vulgarisation": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faComment",
                "border": "boxrule=1pt",
                "background": ""
            },
            "recap": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faClipboardList",
                "border": "boxrule=1pt",
                "background": ""
            }
        }
    
    # Ajouter les couleurs aux options de boîtes
    for box_type, color in box_styles.items():
        if box_type in box_options:
            box_options[box_type]["color"] = color
    
    # Préparer les titres en fonction de la langue cible
    titles = {
        "french": {
            "aretenir": "À retenir",
            "retenir": "À retenir",
            "intuition": "Intuition",
            "vulgarisation": "Vulgarisation simple",
            "recap": "Fiche Récapitulative"
        },
        "english": {
            "aretenir": "Key Points",
            "retenir": "Key Points",
            "intuition": "Intuition",
            "vulgarisation": "Simple Explanation",
            "recap": "Summary Sheet"
        },
        "german": {
            "aretenir": "Zu behalten",
            "retenir": "Zu behalten",
            "intuition": "Intuition",
            "vulgarisation": "Einfache Erklärung",
            "recap": "Zusammenfassung"
        },
        "spanish": {
            "aretenir": "Puntos clave",
            "retenir": "Puntos clave",
            "intuition": "Intuición",
            "vulgarisation": "Explicación simple",
            "recap": "Resumen"
        }
    }
    
    lang_titles = titles.get(target_language, titles["french"])
    
    # Générer les définitions des environnements tcolorbox personnalisés
    tcolorbox_definitions = []
    
    if include_retenir:
        retenir_style = generate_box_style("retenir", box_options.get("retenir", {}), lang_titles)
        tcolorbox_definitions.append(retenir_style)
    
    if include_intuition:
        intuition_style = generate_box_style("intuition", box_options.get("intuition", {}), lang_titles)
        tcolorbox_definitions.append(intuition_style)
    
    if include_vulgarisation:
        vulgarisation_style = generate_box_style("vulgarisation", box_options.get("vulgarisation", {}), lang_titles)
        tcolorbox_definitions.append(vulgarisation_style)
    
    if include_recap:
        recap_style = generate_box_style("recap", box_options.get("recap", {}), lang_titles)
        tcolorbox_definitions.append(recap_style)
    
    # Joindre les définitions des environnements tcolorbox
    tcolorbox_setup = "\n\n".join(tcolorbox_definitions)
    
    # Préparer les instructions sur les boîtes
    box_instructions = ""
    if include_retenir:
        box_instructions += f"""
- **Inclure des boîtes "À retenir"** pour les points clés, en utilisant la syntaxe:
  ```latex
  \\begin{{retenir}}
  Contenu à retenir...
  \\end{{retenir}}
  ```
  Ces boîtes doivent contenir les formules clés, définitions importantes et points à mémoriser.
"""
    
    if include_intuition:
        box_instructions += f"""
- **Inclure des boîtes "Intuition"** pour les explications intuitives, en utilisant la syntaxe:
  ```latex
  \\begin{{intuition}}
  Explication intuitive...
  \\end{{intuition}}
  ```
  Ces boîtes doivent donner des explications accessibles sur des concepts complexes, utiliser des analogies ou des illustrations.
"""
    
    if include_vulgarisation:
        vulgz_descriptions = {
            0: "",
            1: "(niveau minimal - termes techniques conservés)",
            2: "(niveau léger - quelques simplifications)",
            3: "(niveau modéré - analogies courantes)",
            4: "(niveau élevé - analogies quotidiennes)",
            5: "(niveau maximal - explications très simplifiées)"
        }
        box_instructions += f"""
- **Inclure des boîtes "Vulgarisation" {vulgz_descriptions[vulgarization_level]}** en utilisant la syntaxe:
  ```latex
  \\begin{{vulgarisation}}
  Explication vulgarisée...
  \\end{{vulgarisation}}
  ```
  Adapter le niveau selon le paramètre demandé ({vulgarization_level}/5): plus le niveau est élevé, plus l'explication doit être simple.
"""
    
    if include_recap:
        box_instructions += f"""
- **Inclure des boîtes "Fiche Récapitulative"** UNIQUEMENT à la fin de chaque section majeure (pas après les sous-sections), en utilisant cette syntaxe:
  ```latex
  \\begin{{recap}}
  
  \\textbf{{Objectif :}} Résumer le concept principal de cette section.
  
  \\textbf{{Principe central :}} Expliquer l'idée fondamentale.
  
  \\vspace{{0.4em}}
  \\textbf{{Points essentiels :}}  
  - Point important 1
  - Point important 2
  - Point important 3
  
  \\vspace{{0.4em}}
  \\textbf{{Formules clés :}}  
  \\begin{{itemize}}
  \\item $E = mc^2$
  \\item $F = ma$
  \\end{{itemize}}
  
  \\end{{recap}}
  ```
  
  Directives pour les fiches récapitulatives :
  1. Utiliser une structure claire avec sous-titres en gras 
  2. Ne les placer qu'à la fin des sections principales, pas des sous-sections
  3. Synthétiser efficacement les points clés de la section
  4. Inclure les formules mathématiques importantes
  5. Organiser le contenu pour faciliter la révision rapide
"""
    
    # Convertir les pages du PDF en images
    page_images = convert_pdf_pages_to_images(pdf_path)
    if not page_images:
        return f"""% Erreur lors de la génération automatique
\\section{{Erreur}}
La conversion du PDF en images a échoué.
"""
    
    # Construire le prompt
    prompt = f"""Tu es un expert LaTeX spécialisé dans la création de polycopiés pédagogiques structurés à partir de présentations et documents techniques. Ta tâche est de convertir les pages de ce document en un document LaTeX bien structuré.

CONSIGNES GÉNÉRALES :
1. Langue du document : {target_language}
2. Titre du document : "{course_title or 'Document LaTeX'}"
3. Structure complète et claire avec:
   - Chapitres (\\section{{...}})
   - Sous-chapitres (\\subsection{{...}})
   - Sous-sous-chapitres si nécessaire (\\subsubsection{{...}})
4. Reproduire tout le contenu visible, y compris le texte, les équations et les tableaux
5. IMPORTANT: Transformer les bullet points en paragraphes fluides lorsque cela améliore la lisibilité et le flux du texte

TRÈS IMPORTANT: NE PAS INCLURE LES BALISES \\documentclass, \\begin{{document}}, \\end{{document}} ou tout autre préambule.
FOURNIR UNIQUEMENT LE CONTENU DU CORPS DU DOCUMENT (sections, sous-sections, texte, équations, etc.).

ÉLÉMENTS À INCLURE:
1. **Formules mathématiques** : utiliser les environnements equation, align, etc.
2. **Listes** : utiliser itemize pour les listes à puces, enumerate pour les listes numérotées
   - Mais convertir les listes courtes en paragraphes si elles sont plus appropriées sous cette forme
   - Conserver les listes uniquement quand elles apportent une meilleure structure
3. **Tableaux** : recréer les tableaux avec l'environnement tabular
4. **Images** : indiquer l'emplacement des figures avec des commentaires (% FIGURE: description)
5. **Code source** : utiliser l'environnement lstlisting comme ceci:
   ```latex
   \\begin{{lstlisting}}
   // Code source ici (sans accents)
   \\end{{lstlisting}}
   ```

BOÎTES SPÉCIALES DEMANDÉES:
{box_instructions}
"""

    # AJOUTER CETTE CLARIFICATION EXPLICITE SI DES BOÎTES SONT DEMANDÉES
    if include_intuition or include_retenir or include_vulgarisation or include_recap:
        prompt += """
ATTENTION - ÉLÉMENT TRÈS IMPORTANT: Tu DOIS absolument inclure TOUTES les boîtes spéciales demandées ci-dessus.
Il est essentiel que ces boîtes apparaissent à des endroits pertinents du document.
Ne pas oublier d'ajouter ces boîtes, elles sont une partie cruciale de cette tâche.
"""

    prompt += """
INSTRUCTIONS SPÉCIFIQUES POUR LES BLOCS DE CODE:
- Dans les blocs de code (\\begin{lstlisting}...\\end{lstlisting}), utiliser UNIQUEMENT des caractères ASCII
- Remplacer les caractères accentués (é→e, è→e, à→a, etc.)
- Ne pas échapper les % dans les blocs de code

RÈGLES IMPORTANTES:
1. Ne jamais mettre d'accents ou caractères spéciaux dans les blocs de code
2. Vérifier que tous les environnements (tcolorbox, lstlisting) sont bien fermés
3. Éviter la duplication de sections
4. Ne pas inclure d'instructions ou commentaires métadonnées
5. Préférer un style rédactionnel fluide avec des paragraphes bien formés plutôt que des listes excessives
6. Ne pas inclure \\begin{document} ou \\end{document} - seulement le contenu!

FORMATAGE DU DOCUMENT:
- Le préambule LaTeX avec les packages nécessaires est déjà prêt, concentre-toi uniquement sur le contenu
- Utiliser une structure logique qui reflète la hiérarchie du document original
- Inclure des sauts de page (\\newpage) aux endroits appropriés
- Favoriser un style de rédaction académique fluide plutôt qu'une présentation par points

Génère uniquement le contenu LaTeX en suivant ces instructions, sans préambule ni balises de document.
"""

    # Préparer le contenu à envoyer à l'API
    content = [{"type": "text", "text": prompt}]
    
    # Ajouter les images des pages
    for i, img_base64 in enumerate(page_images):
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_base64}",
                "detail": "high"
            }
        })
    
    # Envoyer la requête à l'API
    try:
        # Pour GPT-4o avec vision
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=4096,
            temperature=temperature
        )
        
        # Extraire le contenu brut
        raw_latex_content = response.choices[0].message.content.strip()
        
        # Supprimer les délimiteurs de code Markdown manuellement
        latex_content = raw_latex_content
        if latex_content.startswith('```latex'):
            latex_content = latex_content[8:].lstrip()
        if latex_content.endswith('```'):
            latex_content = latex_content[:-3].rstrip()
            
        # Suppression manuelle des balises \begin{document} et \end{document}
        latex_content = latex_content.replace('\\begin{document}', '')
        latex_content = latex_content.replace('\\end{document}', '')
        
        # Nettoyage final pour supprimer les instructions techniques qui pourraient rester
        instructions_techniques = [
            r"Insérer des \\vspace\{0\.4em\} entre les sections",
            r"Mettre en gras \(\\textbf\) les titres des sections",
            r"\\textbf\{À retenir :\}[^}]*\\begin\{itemize\}",
            r"- Insérer des \\vspace",
            r"- Mettre en gras",
            r"\\end{itemize}\}"
        ]
        
        for pattern in instructions_techniques:
            latex_content = re.sub(pattern, "", latex_content)
        
        # Nettoyage final
        latex_content = latex_content.strip()
        
        return latex_content
        
    except Exception as e:
        print(f"Erreur lors de la conversion du PDF en LaTeX: {str(e)}")
        # Fallback: renvoyer un document minimal avec l'erreur
        return f"""% Erreur lors de la génération automatique
\\section{{Erreur}}
Une erreur s'est produite lors de la conversion du document PDF en LaTeX: {str(e)}
"""

def analyze_slide(
    slide_text: str, 
    context: CourseContext, 
    source_language: str = "french",
    target_language: str = "french", 
    include_intuition: bool = False,
    include_retenir: bool = False,
    include_vulgarisation: bool = False,
    include_recap: bool = False,
    box_styles: dict = None,
    vulgarization_level: int = 0,
    boxOptions: dict = None,
    model: str = "gpt-4"
) -> dict:
    # Si la slide est vide, renvoyer des champs vides
    if not slide_text.strip():
        print("Slide vide détectée.")
        return {
            "content": "",
            "algorithm": "",
            "aretenir": "",
            "intuition": "",
            "vulgarisation": ""
        }
    
    # Styles par défaut si non spécifiés
    if box_styles is None:
        box_styles = {
            "intuition": "green",
            "retenir": "yellow",
            "vulgarisation": "blue",
            "recap": "purple"
        }
    
    # Options de boîtes par défaut si non spécifiées
    if boxOptions is None:
        boxOptions = {
            "retenir": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faBookmark",
                "border": "boxrule=1pt",
                "background": ""
            },
            "intuition": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faLightbulb",
                "border": "boxrule=1pt",
                "background": ""
            },
            "vulgarisation": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faComment",
                "border": "boxrule=1pt",
                "background": ""
            },
            "recap": {
                "titleFont": "lmr",
                "contentFont": "lmr",
                "icon": "\\faClipboardList",
                "border": "boxrule=1pt",
                "background": ""
            }
        }
    
    # Détecter la langue d'origine si non spécifiée
    if source_language == "auto":
        source_language = detect_language(slide_text)
    print(f"Langue source : {source_language}")
    print(f"Langue cible : {target_language}")
    print(f"Inclure intuition : {include_intuition}")
    print(f"Inclure à retenir : {include_retenir}")
    print(f"Inclure vulgarisation : {include_vulgarisation}")
    print(f"Inclure fiche récap : {include_recap}")
    print(f"Niveau de vulgarisation : {vulgarization_level}")
    print(f"Styles des boîtes : {box_styles}")
    
    # Définir les titres en fonction de la langue cible
    titles = {
        "french": {
            "aretenir": "À retenir",
            "intuition": "Intuition",
            "vulgarisation": "Vulgarisation simple"
        },
        "english": {
            "aretenir": "Key Points",
            "intuition": "Intuition",
            "vulgarisation": "Simple Explanation"
        },
        "hebrew": {
            "aretenir": "נקודות מפתח",
            "intuition": "אינטואיציה",
            "vulgarisation": "הסבר פשוט"
        }
    }
    
    lang_titles = titles.get(target_language, titles["french"])
    
    # Configuration pour l'hébreu
    rtl_config = ""
    if target_language == "hebrew":
        rtl_config = f"""
{BACKSLASH}usepackage{{polyglossia}}
{BACKSLASH}setmainlanguage{{hebrew}}
{BACKSLASH}setotherlanguage{{english}}
{BACKSLASH}newfontfamily{BACKSLASH}hebrewfont[Script=Hebrew]{{Arial}}
{BACKSLASH}newfontfamily{BACKSLASH}englishfont[Script=Latin]{{Arial}}
"""
    
    # Définir le niveau de vulgarisation dans le prompt
    vulgarization_instruction = ""
    if include_vulgarisation and vulgarization_level > 0:
        vulgarization_instruction = f"""
Niveau de vulgarisation demandé : {vulgarization_level}/5
- Niveau 1 : Explications minimales, termes techniques conservés
- Niveau 2 : Quelques simplifications, analogies simples
- Niveau 3 : Explications détaillées, analogies courantes
- Niveau 4 : Explications très détaillées, analogies quotidiennes
- Niveau 5 : Explications maximales, analogies enfantines, vocabulaire très simple
"""
    
    # Définir les styles de boîtes
    box_style_instructions = ""
    if include_retenir:
        retenir_icon = boxOptions.get('retenir', {}).get('icon', '\\faBookmark')
        box_style_instructions += f"""
5. Pour les points clés, utilise exactement cette structure (copie-la telle quelle) :

\\begin{{tcolorbox}}[title={{À retenir}}]
Le contenu des points à retenir ici...
\\end{{tcolorbox}}

"""
    if include_intuition:
        intuition_icon = boxOptions.get('intuition', {}).get('icon', '\\faLightbulb')
        box_style_instructions += f"""
6. Pour les intuitions, utilise exactement cette structure (copie-la telle quelle) :

\\begin{{tcolorbox}}[title={{Intuition}}]
Le contenu des intuitions ici...
\\end{{tcolorbox}}

"""
    if include_vulgarisation:
        vulgarisation_icon = boxOptions.get('vulgarisation', {}).get('icon', '\\faComment')
        box_style_instructions += f"""
7. Pour les vulgarisations, utilise exactement cette structure (copie-la telle quelle) :

\\begin{{tcolorbox}}[title={{Vulgarisation simple}}]
Le contenu des vulgarisations ici...
\\end{{tcolorbox}}

"""
    if include_recap:
        recap_icon = boxOptions.get('recap', {}).get('icon', '\\faClipboardList')
        box_style_instructions += f"""
8. Pour les fiches récapitulatives, utilise exactement cette structure (copie-la telle quelle) :

\\begin{{tcolorbox}}[title={{Fiche Récapitulative}}]
Le contenu des fiches récapitulatives ici...
\\end{{tcolorbox}}

"""
    
    prompt = f"""
Tu es un assistant pédagogique expert en création de polycopiés en LaTeX.
Le cours s'appelle : {context.course_title}
Voici le contexte précédent : {context.previous_slide_summary}

{vulgarization_instruction}

Voici le contenu de la slide à transformer (en {source_language}) :
{slide_text}

Transforme ce contenu en un polycopié pédagogique en LaTeX de manière synthétique et structurée.
IMPORTANT : Si la langue cible est le français, tout le contenu doit être en français.
Langue cible : {target_language}

Respecte ces consignes LaTeX :
1. Structure le contenu avec des sections et sous-sections appropriées :
   - Utilise \\section{{...}} pour les grands thèmes
   - Utilise \\subsection{{...}} pour les sous-thèmes
2. Le texte principal ("content") doit être en paragraphes courts et clairs
3. Pour les listes à puces :
   - Utilise \\begin{{itemize}} \\item ... \\end{{itemize}} pour les listes non numérotées
   - Utilise \\begin{{enumerate}} \\item ... \\end{{enumerate}} pour les listes numérotées
4. Pour le code, utilise UNIQUEMENT cette structure très simple :

\\begin{{lstlisting}}
// Exemple de code - SANS caractères accentués
int main() {{
    printf("Hello");
    return 0;
}}
\\end{{lstlisting}}

CONSIGNES IMPORTANTES POUR LE CODE:
- Dans les blocs de code, utilise UNIQUEMENT des caractères ASCII (a-z, A-Z, 0-9, symboles)
- N'utilise JAMAIS de caractères accentués dans les blocs de code (é→e, è→e, à→a)
- Évite complètement les séquences d'échappement de type \\e, \\a, \\b, \\f, \\v
- Pour les commentaires en français dans le code, utilise des versions sans accents

{box_style_instructions}

IMPORTANT :
- Utilise UNIQUEMENT les commandes LaTeX les plus basiques
- Évite les caractères spéciaux ou échappe-les correctement : $ % # & _ {{ }}
- TRAITE AVEC SOIN LES SYMBOLES % DANS LE CODE - ne les échappe PAS avec \\ dans les blocs lstlisting
- Pour les pourcentages dans le texte normal, écris \\%
- Dans les blocs lstlisting, laisse les % tels quels sans les échapper
- DANS LES BLOCS DE CODE, remplace TOUS les caractères accentués (é→e, è→e, etc.)
- TOUT le contenu doit être en {target_language} (sauf les caractères accentués dans les blocs de code)
- Vérifie que tous les environnements tcolorbox sont bien fermés
- Pour les environnements tcolorbox, assure-toi que le format est strict: \\begin{{tcolorbox}}[title={{Titre}}] ... \\end{{tcolorbox}}
- ÉVITE ABSOLUMENT les répétitions de sections et de contenu
- Ne pas inclure d'instructions de formatage dans le contenu du document

Retourne uniquement une réponse en JSON avec ces clés :
{{
  "content": "...",     // Texte principal en LaTeX
  "algorithm": "...",   // Bloc de code en LaTeX ou chaîne vide
  "aretenir": "...",    // Bloc "À retenir" en LaTeX ou chaîne vide
  "intuition": "...",   // Bloc "Intuition" en LaTeX ou chaîne vide
  "vulgarisation": "..." // Bloc "Vulgarisation" en LaTeX ou chaîne vide (uniquement si vulgarization_level > 0)
}}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    clean_content = response.choices[0].message.content.strip()
    # Supprimer les caractères de contrôle
    clean_content = re.sub(r'[\x00-\x1f]+', '', clean_content)
    try:
        # Essayer de décoder avec différentes stratégies pour éviter les erreurs UTF-8
        try:
            json_content = clean_content
            # Encoder puis décoder pour nettoyer les caractères non valides
            json_content_bytes = json_content.encode('utf-8', errors='ignore')
            json_content = json_content_bytes.decode('utf-8', errors='replace')
            json_response = json.loads(json_content)
        except json.JSONDecodeError:
            # Essayer en supprimant les caractères non-ASCII
            json_content = ''.join(c for c in clean_content if ord(c) < 128)
            json_response = json.loads(json_content)
            
        context.update_context(json_response.get("content", ""))
        return json_response
    except json.JSONDecodeError as e:
        print(f"Erreur de parsing JSON : {e}\nRéponse GPT: {clean_content}")
        return {
            "content": slide_text,
            "algorithm": "",
            "aretenir": "",
            "intuition": "",
            "vulgarisation": ""
        }

def correct_latex(latex_content: str) -> str:
    """
    Envoie le contenu LaTeX généré à un modèle plus rapide pour correction syntaxique.
    """
    prompt = f"""
En tant qu'expert LaTeX, vérifie et corrige le code LaTeX suivant pour qu'il compile correctement.
Corrige uniquement la syntaxe, les environnements et la structure, sans modifier le contenu.
Assure-toi que :
- Tous les environnements (tcolorbox, lstlisting, itemize, etc.) sont correctement ouverts et fermés
- Les accolades {{ }} et crochets [ ] sont correctement appariés
- Les caractères spéciaux sont correctement échappés (_, &, %, #, etc.)
- Les commandes LaTeX sont correctement formatées
- Il n'y a pas de lignes vides superflues qui pourraient causer des erreurs

Voici le code LaTeX à corriger :

{latex_content}

Retourne uniquement le code LaTeX corrigé, sans commentaires ni explications.
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Modèle plus rapide
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    
    corrected_latex = response.choices[0].message.content.strip()
    return corrected_latex

def generate_box_style(box_type, options, titles):
    """
    Génère une configuration tcolorbox complète basée sur les options fournies.
    
    Args:
        box_type (str): Type de boîte ('intuition', 'retenir', 'vulgarisation', 'recap')
        options (dict): Options de style pour cette boîte
        titles (dict): Dictionnaire des titres par type de boîte
        
    Returns:
        str: Configuration LaTeX pour la boîte
    """
    # Obtenir les valeurs des options ou utiliser des valeurs par défaut
    title_font = options.get('titleFont', 'lmr')
    content_font = options.get('contentFont', 'lmr')
    icon = options.get('icon', '')
    border = options.get('border', 'boxrule=1pt')
    background = options.get('background', '')
    color = options.get('color', '')
    
    # Mapper les polices aux commandes LaTeX correspondantes
    font_commands = {
        'lmr': '\\rmfamily',
        'phv': '\\sffamily',
        'ptm': '\\rmfamily\\fontfamily{ptm}\\selectfont',
        'ppl': '\\rmfamily\\fontfamily{ppl}\\selectfont',
        'pbk': '\\rmfamily\\fontfamily{pbk}\\selectfont'
    }
    
    title_font_cmd = font_commands.get(title_font, '\\rmfamily')
    content_font_cmd = font_commands.get(content_font, '\\rmfamily')
    
    # Mapper les couleurs standard aux définitions LaTeX
    color_mappings = {
        'green': 'colback=green!5!white,colframe=green!75!black',
        'yellow': 'colback=yellow!5!white,colframe=yellow!75!black',
        'blue': 'colback=blue!5!white,colframe=blue!75!black',
        'red': 'colback=red!5!white,colframe=red!75!black',
        'purple': 'colback=purple!5!white,colframe=purple!75!black',
        'gray': 'colback=gray!5!white,colframe=gray!75!black',
        'orange': 'colback=orange!5!white,colframe=orange!75!black',
        'teal': 'colback=teal!5!white,colframe=teal!75!black',
    }
    
    # Utiliser la couleur spécifiée ou obtenir la couleur par défaut pour ce type de boîte
    color_style = color_mappings.get(color, '')
    
    # Définir le style de fond
    bg_style = ''
    if background == 'grid':
        bg_style = 'boxrule=0.4pt, interior style={white grid}, halign=left'
    elif background == 'dots':
        bg_style = 'boxrule=0.4pt, interior style={white small dots}, halign=left'
    elif background == 'crosshatch':
        bg_style = 'boxrule=0.4pt, interior style={crosshatch}, halign=left'
    elif background == 'gradient':
        bg_style = 'boxrule=0.4pt, interior style={left color=white, right color=gray!10}, halign=left'
    
    # Obtenir le titre localisé pour ce type de boîte
    title = titles.get(box_type, box_type.capitalize())
    
    # Construire le titre avec l'icône si elle est spécifiée
    full_title = f"{icon}\\hspace{{0.5em}}{title}" if icon else title
    
    # Construire les options de style tcolorbox
    style_options = []
    if color_style:
        style_options.append(color_style)
    if border:
        style_options.append(border)
    if bg_style:
        style_options.append(bg_style)
    
    # Ajouter les commandes de police pour le titre et le contenu
    options_str = ",\n    ".join(style_options)
    
    # Construire la commande LaTeX pour définir un nouvel environnement tcolorbox
    return f"""\\NewTColorBox[auto counter,number within=section]{{{box_type}}}{{O{{}}}}{{
    {options_str},
    title={{\\textbf{{{full_title}}}}},
    fonttitle={title_font_cmd},
    fontupper={content_font_cmd},
    attach title to upper=\\quad,
    #1
}}"""