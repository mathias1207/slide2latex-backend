# backend/main.py

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
import shutil
import uuid
import os
import asyncio
from backend.course_generator import generate_course_latex
from backend.compile_latex import compile_latex
from dotenv import load_dotenv
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware
import json

load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pour l'instant, tout est autorisé (sécurise ça plus tard)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration des timeouts
PROCESS_TIMEOUT = 300  # 5 minutes
DOWNLOAD_TIMEOUT = 60  # 1 minute

# Définition des langues supportées
class Language(str, Enum):
    FRENCH = "french"
    ENGLISH = "english"
    HEBREW = "hebrew"

class VulgarizationLevel(int, Enum):
    NONE = 0
    MINIMAL = 1
    LIGHT = 2
    MODERATE = 3
    HIGH = 4
    MAXIMAL = 5

UPLOAD_DIR = "./uploads"
OUTPUT_DIR = "./outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(os.environ['PATH'])

@app.get("/health")
async def health_check():
    """Endpoint de vérification de l'état du serveur"""
    return {"status": "ok"}

@app.post("/process/")
async def process(
    file: UploadFile = File(...),
    course_title: str = Form(...),
    source_language: Language = Form(Language.FRENCH),
    target_language: Language = Form(Language.FRENCH),
    include_intuition: bool = Form(False),
    include_retenir: bool = Form(False),
    include_vulgarisation: bool = Form(False),
    include_recap: bool = Form(False),
    box_styles: str = Form("{}"),
    vulgarization_level: int = Form(0)
):
    try:
        print(f"Répertoire OUTPUT_DIR : {OUTPUT_DIR}")
        print(f"OUTPUT_DIR existe : {os.path.exists(OUTPUT_DIR)}")
        
        # Vérifier la taille du fichier (max 10MB)
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Le fichier est trop volumineux (max 10MB)")

        file_id = str(uuid.uuid4())
        upload_path = f"{UPLOAD_DIR}/{file_id}.pdf"
        tex_path = f"{OUTPUT_DIR}/{file_id}.tex"
        
        print(f"Chemins des fichiers :")
        print(f"- upload_path : {upload_path}")
        print(f"- tex_path : {tex_path}")
        
        # Sauvegarder le fichier avec timeout
        try:
            with open(upload_path, "wb") as buffer:
                await asyncio.wait_for(
                    asyncio.to_thread(shutil.copyfileobj, file.file, buffer),
                    timeout=PROCESS_TIMEOUT
                )
            print(f"Fichier PDF sauvegardé avec succès : {upload_path}")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Timeout lors de la sauvegarde du fichier")

        # Générer le LaTeX avec timeout
        try:
            complete_latex = await asyncio.wait_for(
                asyncio.to_thread(
                    generate_course_latex,
                    upload_path,
                    course_title,
                    source_language=source_language,
                    target_language=target_language,
                    include_intuition=include_intuition,
                    include_retenir=include_retenir,
                    include_vulgarisation=include_vulgarisation,
                    include_recap=include_recap,
                    box_styles=json.loads(box_styles),
                    vulgarization_level=vulgarization_level
                ),
                timeout=PROCESS_TIMEOUT
            )
            print("LaTeX généré avec succès")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Timeout lors de la génération du LaTeX")

        # Sauvegarder le fichier .tex
        try:
            with open(tex_path, "w", encoding="utf-8") as f:
                await asyncio.wait_for(
                    asyncio.to_thread(f.write, complete_latex),
                    timeout=PROCESS_TIMEOUT
                )
            print(f"Fichier .tex sauvegardé avec succès : {tex_path}")
            print(f"Le fichier .tex existe maintenant : {os.path.exists(tex_path)}")
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Timeout lors de la sauvegarde du fichier .tex")

        return JSONResponse(content={
            "file_id": file_id,
            "tex_path": tex_path,
            "source_language": source_language,
            "target_language": target_language,
            "vulgarization_level": vulgarization_level
        })

    except Exception as e:
        print(f"Erreur lors du traitement : {str(e)}")
        # Nettoyer les fichiers en cas d'erreur
        if 'upload_path' in locals() and os.path.exists(upload_path):
            os.remove(upload_path)
        if 'tex_path' in locals() and os.path.exists(tex_path):
            os.remove(tex_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Une erreur est survenue lors du traitement : {str(e)}"
        )

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    tex_path = f"{OUTPUT_DIR}/{file_id}.tex"
    print(f"Tentative de téléchargement du fichier : {tex_path}")
    print(f"Le répertoire OUTPUT_DIR existe : {os.path.exists(OUTPUT_DIR)}")
    print(f"Le fichier .tex existe : {os.path.exists(tex_path)}")
    
    if not os.path.exists(tex_path):
        print(f"Erreur : Le fichier {tex_path} n'existe pas")
        return JSONResponse(
            status_code=404,
            content={"error": "Fichier .tex non trouvé"}
        )
    
    try:
        print(f"Tentative d'envoi du fichier {tex_path}")
        return FileResponse(
            tex_path,
            media_type="text/plain",
            filename=f"{file_id}.tex"
        )
    except Exception as e:
        print(f"Erreur lors du téléchargement : {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur lors du téléchargement : {str(e)}"}
        )
