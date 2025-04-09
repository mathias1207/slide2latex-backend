import os
import subprocess
import re
import shutil

def preprocess_code_blocks(content):
    """
    Prétraitement minimal des blocs de code pour éviter les problèmes avec les caractères accentués.
    """
    # Identifier les blocs de code (entre \begin{lstlisting} et \end{lstlisting})
    lines = content.split('\n')
    processed_lines = []
    in_listing = False
    
    for line in lines:
        # Détecter le début et la fin des blocs de code
        if '\\begin{lstlisting}' in line:
            in_listing = True
            processed_lines.append(line)
            continue
        elif '\\end{lstlisting}' in line:
            in_listing = False
            processed_lines.append(line)
            continue
            
        # Traitement spécifique pour les lignes dans les blocs de code
        if in_listing:
            # Remplacer les caractères accentués par leurs équivalents ASCII
            accent_map = {
                'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                'à': 'a', 'â': 'a', 'ä': 'a',
                'î': 'i', 'ï': 'i',
                'ô': 'o', 'ö': 'o', 
                'ù': 'u', 'û': 'u', 'ü': 'u',
                'ç': 'c',
                'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
                'À': 'A', 'Â': 'A', 'Ä': 'A',
                'Î': 'I', 'Ï': 'I',
                'Ô': 'O', 'Ö': 'O',
                'Ù': 'U', 'Û': 'U', 'Ü': 'U',
                'Ç': 'C'
            }
            
            for accent, replacement in accent_map.items():
                line = line.replace(accent, replacement)
                
            # Filtrer les caractères non-ASCII
            line = ''.join(c for c in line if ord(c) < 128)
        
        processed_lines.append(line)
        
    return '\n'.join(processed_lines)

def compile_latex(latex_path, output_dir=None):
    """
    Compile un fichier LaTeX en PDF.
    
    Args:
        latex_path (str): Chemin vers le fichier LaTeX à compiler
        output_dir (str, optional): Répertoire de sortie. Si None, utilise le même répertoire que le fichier LaTeX
        
    Returns:
        str: Chemin vers le fichier PDF généré, ou None si la compilation a échoué
    """
    if output_dir is None:
        output_dir = os.path.dirname(latex_path)
    
    # S'assurer que le répertoire de sortie existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Nom du fichier LaTeX sans l'extension
    latex_file = os.path.basename(latex_path)
    latex_name = os.path.splitext(latex_file)[0]
    
    # Chemin du fichier PDF généré
    pdf_path = os.path.join(output_dir, latex_name + ".pdf")
    
    # Chemin du fichier log
    log_path = os.path.join(output_dir, latex_name + ".log")
    
    # Normaliser tous les chemins pour éviter les problèmes d'échappement
    latex_path = os.path.normpath(latex_path)
    output_dir = os.path.normpath(output_dir)
    pdf_path = os.path.normpath(pdf_path)
    log_path = os.path.normpath(log_path)
    
    print(f"Compilation de {latex_path} vers {pdf_path}")
    print(f"Répertoire de sortie: {output_dir}")
    print(f"Environnement PATH actuel: {os.environ.get('PATH', 'Non défini')}")
    print(f"Vérification de pdflatex: {shutil.which('pdflatex')}")
    
    try:
        # Prétraitement du fichier LaTeX pour corriger les erreurs courantes
        with open(latex_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        # Vérifier si le document a une structure correcte
        has_begin_document = "\\begin{document}" in content
        has_end_document = "\\end{document}" in content
        has_documentclass = "\\documentclass" in content
        
        print(f"Structure du document: begin_document={has_begin_document}, end_document={has_end_document}, documentclass={has_documentclass}")
        
        if not has_begin_document or not has_end_document or not has_documentclass:
            print("Document LaTeX incomplet. Structure manquante. Ajout d'une structure minimale...")
            
            # Extraction du contenu principal si nécessaire
            if has_begin_document and has_end_document:
                # Extraction du contenu entre \begin{document} et \end{document}
                match = re.search(r'\\begin{document}(.*?)\\end{document}', content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
            
            # Créer un document minimal
            content = f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[french]{{babel}}
\\usepackage{{tcolorbox}}
\\usepackage{{fontawesome5}}
\\usepackage{{listings}}
\\usepackage{{amsmath}}
\\usepackage{{xcolor}}
\\usepackage{{geometry}}
\\usepackage{{textcomp}}
\\DeclareUnicodeCharacter{{00A0}}{{~}}
\\DeclareUnicodeCharacter{{200B}}{{}}

% Configuration simplifiée des listings
\\lstset{{
    basicstyle=\\ttfamily\\small,
    breaklines=true,
    breakatwhitespace=false,
    keepspaces=true,
    numbers=left,
    numberstyle=\\tiny\\color{{gray}},
    showspaces=false,
    showstringspaces=false,
    showtabs=false,
    tabsize=2
}}

% Configuration de tcolorbox
\\tcbuselibrary{{most}}

% Configuration des marges
\\geometry{{margin=2.5cm}}

\\title{{Document LaTeX}}
\\author{{}}
\\date{{}}

\\begin{{document}}
\\maketitle
\\tableofcontents
\\newpage

{content}

\\end{{document}}
"""
        
        # Traiter les blocs de code pour les caractères accentués
        content = preprocess_code_blocks(content)
        
        with open(latex_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(content)
        
        # Exécuter pdflatex pour compiler le document
        print(f"Compilation de {latex_path}")
        
        # Traiter les éventuels conflits de packages
        max_iterations = 3  # Limiter le nombre de tentatives de compilation
        success = False
        errors = []
        
        for i in range(max_iterations):
            cmd = [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={output_dir}",
                latex_path
            ]
            
            print(f"Exécution de la commande: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            print(f"Code de retour: {process.returncode}")
            print(f"Erreur standard: {stderr}")
            
            # Enregistrer les logs pour analyse
            with open(os.path.join(output_dir, f"compile_log_{i+1}.txt"), "w", encoding="utf-8") as log_file:
                log_file.write(f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")
            
            if process.returncode == 0:
                success = True
                print(f"Compilation réussie (itération {i+1})")
                # Nous devons toujours faire au moins 2 compilations pour la table des matières
                # Si c'est la première itération, on continue pour la table des matières
                # Si c'est la deuxième ou plus et que c'est un succès, on peut s'arrêter
                if i >= 1:
                    break
            else:
                print(f"Erreur lors de la compilation (itération {i+1})")
                # Collecter les messages d'erreur en recherchant les lignes pertinentes
                error_lines = []
                
                for line in stdout.split('\n'):
                    if any(err in line.lower() for err in ['error', 'fatal', 'undefined']):
                        error_lines.append(line.strip())
                
                if error_lines:
                    print(f"Erreurs détectées: {error_lines}")
                    errors.extend(error_lines)
                
                # Vérifier s'il y a des erreurs spécifiques liées aux packages
                package_errors = [line for line in error_lines if 'package' in line.lower()]
                if package_errors:
                    print(f"Erreurs liées aux packages: {package_errors}")
                    # Si nous trouvons des erreurs liées aux packages, nous pourrions essayer de les résoudre ici
                    # Pour l'instant, nous nous contentons de les signaler
        
        # Vérifier si le PDF a été généré
        if os.path.exists(pdf_path) and success:
            print(f"PDF généré avec succès: {pdf_path}")
            print(f"Taille du PDF: {os.path.getsize(pdf_path)} octets")
            return pdf_path
        else:
            error_message = "\n".join(errors) if errors else "Raison inconnue"
            print(f"Le PDF n'a pas été généré. Erreurs: {error_message}")
            print(f"Vérification du fichier log...")
            
            # Lire le fichier log s'il existe
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='replace') as log_file:
                    log_content = log_file.read()
                    print(f"Extraits du fichier log:")
                    # Extraire les 20 dernières lignes du log qui contiennent souvent les erreurs
                    log_lines = log_content.split('\n')
                    for line in log_lines[-50:]:
                        if any(err in line.lower() for err in ['error', 'fatal', 'undefined', 'warning']):
                            print(f"LOG ERROR: {line.strip()}")
            else:
                print(f"Fichier log non trouvé: {log_path}")
            
            print("L'utilisateur devra compiler le fichier LaTeX avec Overleaf.")
            return None
    
    except Exception as e:
        print(f"Erreur lors de la compilation: {str(e)}")
        import traceback
        traceback.print_exc()
        return None 