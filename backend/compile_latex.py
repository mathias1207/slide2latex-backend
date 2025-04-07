import os
import subprocess
from pathlib import Path

def compile_latex(tex_file: str, output_dir: str = None) -> str:
    """
    Compile un fichier LaTeX en PDF en utilisant XeLaTeX.
    Retourne le chemin du fichier PDF généré.
    """
    if output_dir is None:
        output_dir = os.path.dirname(tex_file)
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Définir le chemin du fichier PDF de sortie
    pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(tex_file))[0] + '.pdf')
    
    # Vérifier si le fichier PDF existe déjà et le supprimer
    if os.path.exists(pdf_file):
        os.remove(pdf_file)
    
    try:
        # Utiliser le chemin absolu vers xelatex
        xelatex_path = "/Library/TeX/texbin/xelatex"
        
        # Première compilation
        subprocess.run([
            xelatex_path,
            '-interaction=nonstopmode',
            '-output-directory=' + output_dir,
            tex_file
        ], check=True)
        
        # Deuxième compilation pour les références croisées
        subprocess.run([
            xelatex_path,
            '-interaction=nonstopmode',
            '-output-directory=' + output_dir,
            tex_file
        ], check=True)
        
        return pdf_file
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la compilation : {e}")
        return None 