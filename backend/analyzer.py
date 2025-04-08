# backend/analyzer.py

import os
from dotenv import load_dotenv
load_dotenv()
import json
import re
from langdetect import detect, DetectorFactory
from openai import OpenAI
from backend.context import CourseContext

# Pour rendre la détection de langue plus cohérente
DetectorFactory.seed = 0

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_language(text: str) -> str:
    """Détecte la langue d'un texte."""
    try:
        return detect(text)
    except:
        return "en"  # Langue par défaut si la détection échoue

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
    boxOptions: dict = None
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
        rtl_config = r"""
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
\newfontfamily\hebrewfont[Script=Hebrew]{Arial}
\newfontfamily\englishfont[Script=Latin]{Arial}
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
        box_style_instructions += f"""
5. Pour les points clés, utilise :
   \\begin{{tcolorbox}}[
     colback={box_styles['retenir']}!10,
     colframe={box_styles['retenir']},
     title={{\\fontfamily{{{boxOptions['retenir']['titleFont']}}}\\selectfont {boxOptions['retenir']['icon']}\\ {lang_titles['aretenir']}}},
     fonttitle=\\bfseries,
     fontupper=\\fontfamily{{{boxOptions['retenir']['contentFont']}}}\\selectfont,
     {boxOptions['retenir']['border']},
     sharp corners,
     {f"interior style={boxOptions['retenir']['background']}" if boxOptions['retenir']['background'] else ""}
   ]
   ... contenu ...
   \\end{{tcolorbox}}
"""
    if include_intuition:
        box_style_instructions += f"""
6. Pour les intuitions, utilise :
   \\begin{{tcolorbox}}[
     colback={box_styles['intuition']}!10,
     colframe={box_styles['intuition']},
     title={{\\fontfamily{{{boxOptions['intuition']['titleFont']}}}\\selectfont {boxOptions['intuition']['icon']}\\ {lang_titles['intuition']}}},
     fonttitle=\\bfseries,
     fontupper=\\fontfamily{{{boxOptions['intuition']['contentFont']}}}\\selectfont,
     {boxOptions['intuition']['border']},
     sharp corners,
     {f"interior style={boxOptions['intuition']['background']}" if boxOptions['intuition']['background'] else ""}
   ]
   ... contenu ...
   \\end{{tcolorbox}}
"""
    if include_vulgarisation:
        box_style_instructions += f"""
7. Pour les vulgarisations, utilise :
   \\begin{{tcolorbox}}[
     colback={box_styles['vulgarisation']}!10,
     colframe={box_styles['vulgarisation']},
     title={{\\fontfamily{{{boxOptions['vulgarisation']['titleFont']}}}\\selectfont {boxOptions['vulgarisation']['icon']}\\ {lang_titles['vulgarisation']}}},
     fonttitle=\\bfseries,
     fontupper=\\fontfamily{{{boxOptions['vulgarisation']['contentFont']}}}\\selectfont,
     {boxOptions['vulgarisation']['border']},
     sharp corners,
     {f"interior style={boxOptions['vulgarisation']['background']}" if boxOptions['vulgarisation']['background'] else ""}
   ]
   ... contenu ...
   \\end{{tcolorbox}}
"""
    if include_recap:
        box_style_instructions += f"""
8. Pour les fiches récapitulatives, utilise :
   \\begin{{tcolorbox}}[
     colback={box_styles['recap']}!10,
     colframe={box_styles['recap']},
     title={{\\fontfamily{{{boxOptions['recap']['titleFont']}}}\\selectfont {boxOptions['recap']['icon']}\\ Fiche Récapitulative}},
     fonttitle=\\bfseries,
     fontupper=\\fontfamily{{{boxOptions['recap']['contentFont']}}}\\selectfont,
     {boxOptions['recap']['border']},
     sharp corners,
     {f"interior style={boxOptions['recap']['background']}" if boxOptions['recap']['background'] else ""}
   ]
   ... contenu ...
   \\end{{tcolorbox}}
"""
    
    prompt = rf"""
Tu es un assistant pédagogique expert en création de polycopiés en LaTeX.
Le cours s'appelle : {context.course_title}
Voici le contexte précédent : {context.previous_slide_summary}

{vulgarization_instruction}

Voici le contenu de la slide à transformer (en {source_language}) :
{slide_text}

Transforme ce contenu en un polycopié pédagogique en LaTeX de manière synthétique et structurée.
IMPORTANT : Traduis tout le contenu en {target_language} si ce n'est pas déjà le cas.
{vulgarization_instruction}

Respecte les consignes suivantes :
1. Structure le contenu avec des sections et sous-sections appropriées :
   - Utilise \section{{...}} pour les grands thèmes
   - Utilise \subsection{{...}} pour les sous-thèmes
   - Ajoute un espace après chaque titre de section
2. Le texte principal ("content") doit être rédigé en paragraphes courts et clairs en LaTeX
3. Pour les listes à puces :
   - Convertis les bullet points (•) en listes LaTeX
   - Utilise \begin{{itemize}} pour les listes non numérotées
   - Utilise \begin{{enumerate}} pour les listes numérotées
   - Chaque élément doit commencer par \item
4. Si la slide contient du code, formate-le dans un bloc utilisant l'environnement lstlisting :
   \begin{{lstlisting}}[language=C]
   ... code ...
   \end{{lstlisting}}
   IMPORTANT : 
   - Ajoute une ligne vide avant et après le bloc de code
   - Assure-toi que le code est correctement indenté
   - Remplace les guillemets courbes par des guillemets droits

{box_style_instructions}

IMPORTANT :
- Ne crée jamais d'encadrés imbriqués
- Chaque bloc doit être autonome avec un seul titre
- Échappe correctement les barres obliques inverses (\\\\) pour le JSON
- Structure le texte en paragraphes courts et clairs
- Ajoute des espaces après les titres de sections
- Ajoute une ligne vide avant et après chaque bloc de code ou tcolorbox
- Remplace les guillemets courbes par des guillemets droits dans le code
- Assure-toi que les listes sont correctement formatées avec \item
- Si la langue cible est l'hébreu, assure-toi que le texte est correctement formaté de droite à gauche
- Adapte le niveau de vulgarisation selon le paramètre fourni

Retourne uniquement une réponse en JSON avec exactement ces clés :
{{
  "content": "...",     // Texte principal en LaTeX
  "algorithm": "...",   // Bloc de code en LaTeX ou chaîne vide
  "aretenir": "...",    // Bloc "À retenir" en LaTeX ou chaîne vide
  "intuition": "...",   // Bloc "Intuition" en LaTeX ou chaîne vide
  "vulgarisation": "..." // Bloc "Vulgarisation" en LaTeX ou chaîne vide (uniquement si vulgarization_level > 0)
}}
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    clean_content = response.choices[0].message.content.strip()
    # Supprimer les caractères de contrôle
    clean_content = re.sub(r'[\x00-\x1f]+', '', clean_content)
    try:
        json_response = json.loads(clean_content)
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
