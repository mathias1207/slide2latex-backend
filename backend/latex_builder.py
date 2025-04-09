# backend/latex_builder.py

def build_latex_document(body: str, title: str, language: str = "french", use_all_packages: bool = False, box_setup: str = "") -> str:
    # Configuration pour les langues RTL
    rtl_config = ""
    if language == "hebrew":
        rtl_config = "\\usepackage{polyglossia}\n\\setmainlanguage{hebrew}\n\\setotherlanguage{english}"
    else:
        # Configuration Babel standard pour les autres langues
        rtl_config = f"\\usepackage[{language}]{{babel}}"
    
    # Packages de base toujours inclus - on utilise uniquement ceux-ci quoi qu'il arrive
    essential_packages = [
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage[T1]{fontenc}",
        "\\usepackage{geometry}",
        "\\usepackage{tcolorbox}",
        "\\usepackage{fontawesome5}",
        "\\usepackage{listings}",
        "\\usepackage{amsmath}",
        "\\usepackage{amsfonts}",
        "\\usepackage{amssymb}",
        "\\usepackage{xcolor}",
        "\\usepackage{textcomp}",
        "\\usepackage{graphicx}",  # Required for inserting images
        "\\usepackage[version=4]{mhchem}",
        "\\usepackage{stmaryrd}",
        "\\graphicspath{ {./images/} }",
        "\\usepackage{float}",
        "\\usepackage[linesnumbered,ruled,vlined]{algorithm2e}",
        "\\usepackage{amsthm}",  # pour pouvoir utiliser \newtheorem
        "\\usepackage{pifont}",  # pour les symboles comme ding{55} = ✘
        "\\DeclareUnicodeCharacter{00A0}{~}",
        "\\DeclareUnicodeCharacter{200B}{}",
        "\\usepackage{hyperref}"  # Toujours charger hyperref en dernier
    ]
    
    # On utilise toujours uniquement les packages essentiels, peu importe la valeur de use_all_packages
    all_packages = "\n".join(essential_packages)
    print("Utilisation des packages essentiels uniquement (packages.txt ignoré)")
    
    # Template latex minimal avec la liste de packages
    template = """\\documentclass[12pt]{article}
ALLPACKAGES
RTLCONFIG

% Configuration simplifiée pour éviter les erreurs avec \\hss
\\lstset{
    basicstyle=\\ttfamily\\small,
    breaklines=true,
    breakatwhitespace=false,
    keepspaces=true,
    numbers=left,
    numberstyle=\\tiny\\color{gray},
    showspaces=false,
    showstringspaces=false,
    showtabs=false,
    tabsize=2
}

% Configuration des boîtes tcolorbox
\\tcbuselibrary{most,skins,breakable}

% Configuration par défaut pour les boîtes personnalisées
% Les styles spécifiques sont définis plus bas
\\tcbset{
    sharp corners,
    enhanced,
    breakable,
    fonttitle=\\bfseries,
    top=8pt,
    bottom=8pt,
    left=8pt,
    right=8pt
}

BOX_SETUP

% Ajouter cette commande pour les échappements
\\newcommand{\\escapesym}[1]{\\texttt{\\textbackslash{}#1}}

% Configuration des marges
\\geometry{margin=2.5cm}

\\title{TITLE}
\\author{}
\\date{}

\\begin{document}
\\maketitle
\\tableofcontents
\\newpage

BODY

\\end{document}"""
    
    # Remplacer les placeholders
    template = template.replace("ALLPACKAGES", all_packages)
    template = template.replace("RTLCONFIG", rtl_config)
    template = template.replace("BOX_SETUP", box_setup)
    template = template.replace("TITLE", title)
    template = template.replace("BODY", body)
    
    return template
