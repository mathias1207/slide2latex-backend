# backend/main.py - Version minimaliste

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import shutil
import json
import re
from backend.course_generator import generate_course_latex
from backend.compile_latex import compile_latex

# Initialisation de l'API
app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Répertoires pour les fichiers
TEMP_DIR = "./temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Stockage des chemins de fichiers
file_paths = {}

# Vérification de la santé du serveur
@app.get("/health")
async def health_check():
    """Vérifie si le serveur est en ligne"""
    return {"status": "ok"}

# Traitement simplifié des fichiers PDF
@app.post("/process/")
async def process_file(
    file: UploadFile = File(...),
    course_title: str = Form(None),
    source_lang: str = Form("fr"),
    target_lang: str = Form("fr"),
    include_intuition: bool = Form(False),
    include_retenir: bool = Form(False),
    include_vulgarisation: bool = Form(False),
    include_recap: bool = Form(False),
    box_styles: str = Form("default"),
    box_options: str = Form("default"),
    vulgarization_level: str = Form("medium"),
    model_choice: str = Form("standard"),
    use_all_packages: bool = Form(True)
):
    """Traite un fichier PDF pour le convertir en LaTeX"""
    try:
        # 1. Créer un répertoire unique pour ce traitement
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # 2. Sauvegarder le fichier PDF
        pdf_path = os.path.join(job_dir, f"input_{job_id}.pdf")
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 3. Configuration de base des options
        target_lang_full = get_full_language_name(target_lang)
        source_lang_full = get_full_language_name(source_lang)
        
        if box_styles == "default":
            box_styles_dict = {
                "intuition": "green",
                "retenir": "yellow",
                "vulgarisation": "blue",
                "recap": "purple"
            }
        else:
            try:
                box_styles_dict = json.loads(box_styles)
            except:
                box_styles_dict = {
                    "intuition": "green",
                    "retenir": "yellow",
                    "vulgarisation": "blue",
                    "recap": "purple"
                }
        
        if box_options == "default":
            box_options_dict = {
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
        else:
            try:
                box_options_dict = json.loads(box_options)
            except:
                # Valeurs par défaut en cas d'erreur
                box_options_dict = {
                    "retenir": {"titleFont": "lmr", "contentFont": "lmr", "icon": "\\faBookmark"},
                    "intuition": {"titleFont": "lmr", "contentFont": "lmr", "icon": "\\faLightbulb"},
                    "vulgarisation": {"titleFont": "lmr", "contentFont": "lmr", "icon": "\\faComment"},
                    "recap": {"titleFont": "lmr", "contentFont": "lmr", "icon": "\\faClipboardList"}
                }
        
        vulgarization_map = {
            "none": 0, "minimal": 1, "light": 2, 
            "medium": 3, "high": 4, "maximal": 5
        }
        vulgarization_level_int = vulgarization_map.get(vulgarization_level.lower(), 3)
        
        # 4. Paramètres selon le mode choisi
        model_params = {
            "fast": {"model": "gpt-4o", "temperature": 0.7},
            "standard": {"model": "gpt-4o", "temperature": 0.5},
            "high_quality": {"model": "gpt-4o", "temperature": 0.3},
            "premium": {"model": "gpt-4o", "temperature": 0.2}
        }
        params = model_params.get(model_choice, model_params["standard"])
        
        # 5. Générer le LaTeX (avec gestion d'erreur simple)
        latex_path = os.path.join(job_dir, f"output_{job_id}.tex")
        try:
            # Tentative de génération normale
            latex_content = generate_course_latex(
                pdf_path,
                latex_path,
                course_title=course_title,
                source_lang=source_lang_full,
                target_lang=target_lang_full,
                include_intuition=include_intuition,
                include_retenir=include_retenir,
                include_vulgarisation=include_vulgarisation,
                include_recap=include_recap,
                box_styles=box_styles_dict,
                box_options=box_options_dict,
                vulgarization_level=vulgarization_level_int,
                model=params["model"],
                temperature=params["temperature"],
                use_all_packages=use_all_packages
            )
        except Exception as e:
            # En cas d'erreur, créer un document minimal
            print(f"Erreur de génération LaTeX: {str(e)}")
            latex_content = create_fallback_document(
                course_title=course_title,
                target_lang=target_lang_full,
                error_message=str(e)
            )
        
        # 6. Écrire le fichier LaTeX sur disque
        with open(latex_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(latex_content)
        
        # 7. Enregistrer le chemin pour le téléchargement
        file_paths[job_id] = {
            "tex": latex_path,
            "pdf": None,  # Sera mis à jour si compilation réussie
            "dir": job_dir
        }
        
        # 8. Tenter la compilation PDF (optionnel, ne bloque pas en cas d'échec)
        try:
            pdf_output_path = compile_latex(latex_path, job_dir)
            if pdf_output_path and os.path.exists(pdf_output_path):
                file_paths[job_id]["pdf"] = pdf_output_path
                print(f"PDF généré: {pdf_output_path}")
        except Exception as compile_error:
            print(f"Erreur de compilation PDF: {str(compile_error)}")
            # Sauvegarder l'erreur pour référence
            error_log_path = os.path.join(job_dir, "compile_error.log")
            with open(error_log_path, "w", encoding="utf-8") as error_file:
                error_file.write(f"Erreur de compilation PDF: {str(compile_error)}\n")
                import traceback
                traceback.print_exc(file=error_file)
            # Rendre le fichier log accessible
            file_paths[job_id]["error_log"] = error_log_path
            # Continue même si la compilation échoue
        
        # 9. Retourner l'ID de traitement
        return {"file_id": job_id}
        
    except Exception as e:
        print(f"Erreur de traitement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de traitement: {str(e)}")

# Endpoint simple pour document minimal
@app.post("/simple-pdf/")
async def simple_pdf_process(
    file: UploadFile = File(...),
    course_title: str = Form(None),
    target_lang: str = Form("fr")
):
    """Crée un document LaTeX minimal directement, sans traitement complexe"""
    try:
        # Créer un répertoire unique
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Sauvegarder le fichier PDF (pour référence)
        pdf_path = os.path.join(job_dir, f"input_{job_id}.pdf")
        with open(pdf_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Langue complète
        target_lang_full = get_full_language_name(target_lang)
        
        # Créer un document LaTeX minimal
        latex_path = os.path.join(job_dir, f"output_{job_id}.tex")
        simple_content = create_simple_document(course_title, target_lang_full)
        
        # Écrire le contenu
        with open(latex_path, "w", encoding="utf-8") as f:
            f.write(simple_content)
        
        # Enregistrer pour téléchargement
        file_paths[job_id] = {
            "tex": latex_path,
            "pdf": None,
            "dir": job_dir
        }
        
        # Retourner l'ID
        return {"file_id": job_id, "message": "Document minimal créé avec succès"}
    
    except Exception as e:
        print(f"Erreur dans le traitement simplifié: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Téléchargement de fichier LaTeX
@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """Télécharge le fichier LaTeX généré"""
    if file_id not in file_paths or not file_paths[file_id]["tex"]:
        raise HTTPException(status_code=404, detail="Fichier LaTeX non trouvé")
    
    tex_path = file_paths[file_id]["tex"]
    if not os.path.exists(tex_path):
        raise HTTPException(status_code=404, detail="Fichier LaTeX non trouvé")
    
    filename = f"document_{file_id}.tex"
    return FileResponse(
        path=tex_path,
        filename=filename,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# Téléchargement de fichier PDF (si disponible)
@app.get("/download-pdf/{file_id}")
async def download_pdf(file_id: str):
    """Télécharge le fichier PDF compilé (si disponible)"""
    if file_id not in file_paths:
        raise HTTPException(status_code=404, detail="Aucun fichier trouvé avec cet identifiant")
    
    if not file_paths[file_id]["pdf"] or not os.path.exists(file_paths[file_id]["pdf"]):
        raise HTTPException(
            status_code=404, 
            detail="Le PDF n'a pas pu être généré. Veuillez télécharger le fichier LaTeX et le compiler avec Overleaf."
        )
    
    pdf_path = file_paths[file_id]["pdf"]
    
    filename = f"document_{file_id}.pdf"
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# Téléchargement des logs d'erreur de compilation
@app.get("/error-log/{file_id}")
async def download_error_log(file_id: str):
    """Télécharge les logs d'erreur de compilation LaTeX"""
    if file_id not in file_paths:
        raise HTTPException(status_code=404, detail="Aucun fichier trouvé avec cet identifiant")
    
    # Vérifier si des logs d'erreur existent
    error_log = file_paths[file_id].get("error_log")
    if not error_log or not os.path.exists(error_log):
        # Vérifier s'il y a des logs de compilation générés par pdflatex
        job_dir = file_paths[file_id]["dir"]
        compile_logs = [f for f in os.listdir(job_dir) if f.startswith("compile_log_") or f.endswith(".log")]
        
        if not compile_logs:
            raise HTTPException(
                status_code=404, 
                detail="Aucun log d'erreur disponible pour ce traitement"
            )
        
        # Utiliser le premier log trouvé
        error_log = os.path.join(job_dir, compile_logs[0])
    
    filename = f"error_log_{file_id}.txt"
    return FileResponse(
        path=error_log,
        filename=filename,
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# Fonctions utilitaires
def get_full_language_name(lang_code):
    """Convertit un code de langue en nom complet pour babel"""
    lang_map = {
        "fr": "french", "en": "english", "de": "german", "es": "spanish",
        "it": "italian", "pt": "portuguese", "nl": "dutch", "ru": "russian"
    }
    
    if lang_code in lang_map:
        return lang_map[lang_code]
    elif len(lang_code) == 2:
        # Si code court non reconnu, anglais par défaut
        return "english"
    else:
        # Si c'est déjà un nom complet, le retourner
        return lang_code

def create_fallback_document(course_title=None, target_lang="french", error_message=""):
    """Crée un document LaTeX minimal en cas d'erreur"""
    safe_error = error_message.replace('_', '\\_').replace('%', '\\%').replace('#', '\\#')
    
    return f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[{target_lang}]{{babel}}
\\usepackage{{amsmath}}
\\usepackage{{geometry}}

\\title{{{course_title or "Document de secours"}}}
\\author{{}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle

\\section{{Mode de secours}}
Une erreur est survenue lors de la génération du document.

\\subsection{{Détails de l'erreur}}
{safe_error}

\\subsection{{Recommandations}}
\\begin{{itemize}}
\\item Essayez de réduire la taille du document
\\item Utilisez un fichier PDF différent
\\item Essayez le mode simplifié
\\end{{itemize}}

\\end{{document}}
"""

def create_simple_document(course_title=None, target_lang="french"):
    """Crée un document LaTeX minimal"""
    return f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[{target_lang}]{{babel}}
\\usepackage{{graphicx}}
\\usepackage{{tcolorbox}}
\\usepackage{{listings}}
\\usepackage{{amsmath}}
\\usepackage{{xcolor}}
\\usepackage{{geometry}}

\\geometry{{margin=2.5cm}}
\\title{{{course_title or "Document PDF converti"}}}
\\author{{}}
\\date{{\\today}}

\\begin{{document}}
\\maketitle
\\tableofcontents

\\section{{Introduction}}
Ce document a été généré en mode simplifié.

\\section{{Comment utiliser ce template}}
Vous pouvez modifier ce document pour y ajouter votre contenu:

\\begin{{lstlisting}}
// Exemple de code
function hello() {{
    console.log("Hello World");
}}
\\end{{lstlisting}}

\\begin{{tcolorbox}}[title={{Information}}]
Les boîtes comme celle-ci peuvent être utilisées pour mettre en évidence des informations importantes.
\\end{{tcolorbox}}

\\end{{document}}
"""
