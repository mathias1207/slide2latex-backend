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
    vulgarization_level: VulgarizationLevel = Form(VulgarizationLevel.NONE)
):
    try:
        # Vérifier la taille du fichier (max 10MB)
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Le fichier est trop volumineux (max 10MB)")

        file_id = str(uuid.uuid4())
        upload_path = f"{UPLOAD_DIR}/{file_id}.pdf"
        tex_path = f"{OUTPUT_DIR}/{file_id}.tex"
        
        # Sauvegarder le fichier avec timeout
        try:
            with open(upload_path, "wb") as buffer:
                await asyncio.wait_for(
                    asyncio.to_thread(shutil.copyfileobj, file.file, buffer),
                    timeout=PROCESS_TIMEOUT
                )
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
                    vulgarization_level=vulgarization_level
                ),
                timeout=PROCESS_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Timeout lors de la génération du LaTeX")

        # Sauvegarder le fichier .tex
        try:
            with open(tex_path, "w", encoding="utf-8") as f:
                await asyncio.wait_for(
                    asyncio.to_thread(f.write, complete_latex),
                    timeout=PROCESS_TIMEOUT
                )
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
    pdf_path = f"{OUTPUT_DIR}/{file_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{file_id}.pdf"
        )
    return JSONResponse(
        status_code=404,
        content={"error": "Fichier non trouvé"}
    )
