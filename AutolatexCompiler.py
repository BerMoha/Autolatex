

import streamlit as st
import os
import subprocess
import shutil
from pathlib import Path

# === CONFIGURATION ===
folder = Path(r"C:\Users\BERKANIMO\Desktop\Autolatex")
folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="AutoLaTeX Compiler", layout="centered")

def has_latex_preamble(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '\\documentclass' in content and '\\begin{document}' in content
    except Exception as e:
        st.warning(f"Could not read {filepath}: {e}")
        return False

def compile_latex_file(filepath: Path) -> Path | None:
    filename = filepath.name

    if filename.lower().endswith('.txt') and not has_latex_preamble(filepath):
        return None

    # Rename .txt to .tex if needed
    if filename.lower().endswith('.txt'):
        new_path = filepath.with_suffix('.tex')
        filepath.rename(new_path)
        filepath = new_path
        filename = filepath.name

    output_pdf = filepath.with_suffix('.pdf')

    try:
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={folder}",
                str(filepath)
            ],
            check=True,
            capture_output=True,
            text=True
        )
        return output_pdf
    except subprocess.CalledProcessError as e:
        st.error(f"❌ Compilation failed for {filename}")
        st.code(e.stderr or e.stdout)
    except FileNotFoundError:
        st.error("❌ `pdflatex` not found. Please install MiKTeX or TeX Live and add it to PATH.")
    return None

def cleanup_auxiliary_files():
    for ext in ['.aux', '.log', '.out', '.toc']:
        for file in folder.glob(f"*{ext}"):
            file.unlink(missing_ok=True)

# === INTERFACE STREAMLIT ===

st.title("📄 AutoLaTeX Compiler")

st.markdown("Uploader un fichier `.tex` ou `.txt` contenant une structure LaTeX complète pour le compiler.")

uploaded_file = st.file_uploader("Choisir un fichier LaTeX", type=["tex", "txt"])

if uploaded_file is not None:
    temp_path = folder / uploaded_file.name
    with open(temp_path, 'wb') as f:
        f.write(uploaded_file.read())
    st.success(f"✅ Fichier enregistré : {uploaded_file.name}")

    if st.button("🚀 Compiler le fichier"):
        pdf_path = compile_latex_file(temp_path)
        if pdf_path and pdf_path.exists():
            st.success(f"✅ PDF généré : {pdf_path.name}")
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Télécharger le PDF", f, file_name=pdf_path.name)
            st.components.v1.iframe(str(pdf_path), height=600)
            cleanup_auxiliary_files()
        else:
            st.error("❌ La compilation a échoué ou le fichier est vide.")
