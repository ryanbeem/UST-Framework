import os
import re
from pathlib import Path

# Target directory
BASE_DIR = Path(r"Z:\Manuscript\UST Series")
CHAPTERS_DIR = BASE_DIR / "chapters"

# Create 'chapters' subfolder if it doesn't exist
CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

# Exact 20 filenames mapped by Pillar
PILLARS = {
    "Pillar I: Foundational Core": [
        "UST_Core_Framework_Manifesto.tex",
        "UST-UHF Paper I.tex",
        "UST-UHF Paper II.tex",
        "UST-UHF Paper III.tex",
        "UST-UHF Paper IV.tex",
    ],
    "Pillar II: The Emergence Series": [
        "UST_Core_Emergent_Series.tex",
        "UST-UHF Paper V.tex",
        "UST-UHF Paper VI.tex",
        "UST-UHF Paper VII.tex",
        "UST-UHF Paper VIII.tex",
        "UST-UHF Paper IX.tex",
        "UST-UHF Paper X.tex",
        "UST-UHF Paper XI.tex",
        "UST-UHF Paper XII.tex",
    ],
    "Pillar III: The Cosmology Branch": [
        "UST_Cosmology_Branch_Manifesto.tex",
        "UST-UHF Paper K1.tex",
        "UST-UHF Paper K2.tex",
        "UST-UHF Paper K3.tex",
        "UST-UHF Paper K4.tex",
        "UST-UHF Paper K5.tex",
    ],
}

def clean_file_content(content):
    """Strips preamble, bibliographies, abstracts, keeps body, and converts \\title to \\chapter."""
    doc_match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}', content, re.DOTALL)
    if doc_match:
        body = doc_match.group(1)
    else:
        body = content

    # Strip bibliographies
    body = re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', '', body, flags=re.DOTALL)
    body = re.sub(r'\\bibliography\{.*?\}', '', body)
    body = re.sub(r'\\printbibliography(\[.*?\])?', '', body)

    # Strip abstracts
    body = re.sub(r'\\begin\{abstract\}.*?\\end\{abstract\}', '', body, flags=re.DOTALL)
    body = re.sub(r'\\abstract\{.*?\}', '', body, flags=re.DOTALL)

    # Structural cleanup
    body = re.sub(r'\\title\{([^}]+)\}', r'\\chapter{\1}', body)
    body = re.sub(r'\\maketitle', '', body)
    body = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', body)
    body = re.sub(r'\\usepackage(\[.*?\])?\{.*?\}', '', body)
    
    return body.strip()

# --- STEP 1: Process individual files ---
print("Processing LaTeX files...")
processed_includes = {}

for pillar_name, file_list in PILLARS.items():
    processed_includes[pillar_name] = []
    for filename in file_list:
        file_path = BASE_DIR / filename
        
        if not file_path.exists():
            print(f"  [Warning] Could not find: {filename}. Skipping.")
            continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()

        cleaned_content = clean_file_content(raw_content)

        clean_stem = file_path.stem.replace(" ", "_")
        out_name = f"clean_{clean_stem}.tex"
        out_path = CHAPTERS_DIR / out_name

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        processed_includes[pillar_name].append(f"chapters/{out_name[:-4]}")
        print(f"  [OK] Processed: {filename} -> chapters/{out_name}")

# --- STEP 2: Generate Master main.tex ---
master_tex_path = BASE_DIR / "main.tex"

master_content = [
    r"\documentclass[11pt,a4paper,twoside,openright]{book}",
    r"\usepackage[utf8]{inputenc}",
    r"\usepackage{xcolor}",
    r"",
    r"% --- CORE MATH & THEOREM DEFINITIONS ---",
    r"\usepackage{amsmath,amssymb,amsfonts,amsthm}",
    r"\theoremstyle{plain}",
    r"\newtheorem{thm}{Theorem}[chapter]",
    r"\newtheorem{prop}[thm]{Proposition}",
    r"\newtheorem{lem}[thm]{Lemma}",
    r"\newtheorem{cor}[thm]{Corollary}",
    r"\theoremstyle{definition}",
    r"\newtheorem{defn}[thm]{Definition}",
    r"\newtheorem{exmp}[thm]{Example}",
    r"\theoremstyle{remark}",
    r"\newtheorem{rem}[thm]{Remark}",
    r"",
    r"% --- CODE LISTINGS (Fixes \begin{lstlisting}) ---",
    r"\usepackage{listings}",
    r"\lstset{",
    r"    basicstyle=\ttfamily\small,",
    r"    breaklines=true,",
    r"    commentstyle=\color{gray},",
    r"    keywordstyle=\color{blue},",
    r"    stringstyle=\color{teal},",
    r"    showstringspaces=false",
    r"}",
    r"",
    r"% --- TABLES, GRAPHICS & FLOATS ---",
    r"\usepackage{graphicx}",
    r"\usepackage{booktabs}",
    r"\usepackage{array}",
    r"\usepackage{tabularx}",
    r"\usepackage{multirow}",
    r"\usepackage{placeins}",
    r"",
    r"% --- LAYOUT & HYPERLINKS ---",
    r"\usepackage{geometry}",
    r"\geometry{margin=1in}",
    r"\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}",
    r"\usepackage{bookmark}",
    r"",
    r"\title{\textbf{Unified Substrate Theory (UST)}\\\Large Complete Collected Works: Pillars I, II, \& III}",
    r"\author{\textbf{Ryan Beem}\\Independent Researcher}",
    r"\date{August 2026}",
    r"",
    r"\begin{document}",
    r"\frontmatter",
    r"\maketitle",
    r"\tableofcontents",
    r"",
    r"\mainmatter",
    r""
]

for pillar_name, includes in processed_includes.items():
    master_content.append(f"% {'='*50}")
    master_content.append(f"% {pillar_name.upper()}")
    master_content.append(f"% {'='*50}")
    master_content.append(f"\\part{{{pillar_name}}}")
    for inc_path in includes:
        master_content.append(f"\\include{{{inc_path}}}")
    master_content.append("")

master_content.append(r"\end{document}")

with open(master_tex_path, "w", encoding="utf-8") as f:
    f.write("\n".join(master_content))

print("\n" + "="*50)
print(f"SUCCESS! Master file regenerated with listings support at: {master_tex_path}")
print("="*50)