

import streamlit as st
import requests
from io import BytesIO
from pathlib import Path

# === CONFIGURATION ===
folder = Path(r"C:\Users\BERKANIMO\Desktop\Autolatex")
folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="AutoLaTeX Compiler", layout="centered")

def has_latex_preamble(filepath):
    """Check if the LaTeX file contains the LaTeX preamble."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '\\documentclass' in content and '\\begin{document}' in content
    except Exception as e:
        st.warning(f"Could not read {filepath}: {e}")
        return False

def compile_latex_online(latex_content):
    """Send LaTeX content to QuickLaTeX API for online compilation."""
    url = "https://quicklatex.com/latex3.f"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'formula': latex_content,
        'fsize': '12',
        'fcolor': '000000',
        'bg': 'FFFFFF',
        'mode': '0'
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.content  # PDF content
        else:
            st.error("❌ LaTeX compilation failed!")
            return None
    except Exception as e:
        st.error(f"❌ Error during API request: {e}")
        return None

def cleanup_auxiliary_files():
    """Remove auxiliary files generated during LaTeX compilation."""
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
        # Read the content of the LaTeX file
        with open(temp_path, 'r', encoding='utf-8') as f:
            latex_content = f.read()

        # Check if the LaTeX file has a valid preamble
        if not has_latex_preamble(temp_path):
            st.warning("❌ Le fichier ne contient pas de préambule LaTeX valide. Compilation annulée.")
        else:
            # Send LaTeX content to QuickLaTeX API for compilation
            pdf_content = compile_latex_online(latex_content)
            if pdf_content:
                # Provide the compiled PDF for download
                st.success(f"✅ PDF généré pour {uploaded_file.name}")
                st.download_button("⬇️ Télécharger le PDF", pdf_content, file_name=f"{uploaded_file.name}.pdf")
            else:
                st.error("❌ La compilation a échoué.")

        cleanup_auxiliary_files()
