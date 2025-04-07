# backend/main.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
import shutil
import uuid
import os
from backend.course_generator import generate_course_latex
from backend.compile_latex import compile_latex
from dotenv import load_dotenv
from enum import Enum
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pour l’instant, tout est autorisé (sécurise ça plus tard)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/process/")
async def process(
    file: UploadFile = File(...),
    course_title: str = Form(...),
    source_language: Language = Form(Language.FRENCH),
    target_language: Language = Form(Language.FRENCH),
    vulgarization_level: VulgarizationLevel = Form(VulgarizationLevel.NONE)
):
    file_id = str(uuid.uuid4())
    upload_path = f"{UPLOAD_DIR}/{file_id}.pdf"
    tex_path = f"{OUTPUT_DIR}/{file_id}.tex"
    
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Génération du contenu LaTeX complet à partir du PDF
    complete_latex = generate_course_latex(
        upload_path, 
        course_title, 
        source_language=source_language,
        target_language=target_language,
        vulgarization_level=vulgarization_level
    )

    # Sauvegarde du fichier .tex
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(complete_latex)

    return JSONResponse(content={
        "file_id": file_id, 
        "tex_path": tex_path,
        "source_language": source_language,
        "target_language": target_language,
        "vulgarization_level": vulgarization_level
    })

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
