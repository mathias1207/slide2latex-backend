# backend/latex_builder.py

def build_latex_document(body: str, title: str, language: str = "french") -> str:
    # Configuration pour les langues RTL
    rtl_config = ""
    if language == "hebrew":
        rtl_config = r"""
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{hebrew}
\setotherlanguage{english}
\newfontfamily\hebrewfont[Script=Hebrew]{Arial}
\newfontfamily\englishfont[Script=Latin]{Arial}
\setmainfont{Arial}
\setmonofont{Courier New}
\setRTL
"""
    
    return rf"""% !TEX program = xelatex
\documentclass[12pt]{{report}}
\usepackage[utf8]{{inputenc}}
\usepackage[{language}]{{babel}}
{rtl_config}
\usepackage{{tcolorbox}}
\usepackage{{fontawesome5}}
\usepackage{{listings}}
\usepackage{{algorithm2e}}
\usepackage{{amsmath,amsfonts,amssymb,graphicx,float}}
\usepackage{{xcolor}}
\usepackage{{parskip}}

% Configuration des listings
\lstset{{
    basicstyle=\ttfamily\small,
    breaklines=true,
    frame=single,
    numbers=left,
    numberstyle=\tiny,
    numbersep=5pt,
    showstringspaces=false,
    language=C,
    keepspaces=true,
    columns=flexible,
    literate={{*}}{{\textasteriskcentered}}1
}}

% Configuration des tcolorbox
\tcbuselibrary{{most}}
\newtcolorbox{{mybox}}[1][]{{
    colback=white,
    colframe=black,
    coltitle=black,
    title=#1,
    fonttitle=\bfseries
}}

% Configuration des marges
\usepackage[left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{{geometry}}

\graphicspath{{{{./images/}}}}
\title{{{title}}}
\author{{}}

\begin{{document}}
\maketitle
\tableofcontents
\newpage

\section{{Introduction}}
{body}

\end{{document}}"""
