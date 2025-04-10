

import streamlit as st
import requests
from pathlib import Path

# === CONFIGURATION ===
folder = Path(r"C:\Users\BERKANIMO\Desktop\Autolatex")
folder.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="AutoLaTeX Compiler", layout="centered")

# Function to check if LaTeX content has the preamble
def has_latex_preamble(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '\\documentclass' in content and '\\begin{document}' in content
    except Exception as e:
        st.warning(f"Could not read {filepath}: {e}")
        return False

# Function to send LaTeX content to QuickLaTeX API for compilation
def compile_latex_online(latex_content):
    url = "https://quicklatex.com/latex3.f"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'formula': latex_content, 'fsize': '12', 'fcolor': '000000', 'bg': 'FFFFFF', 'mode': '0'}
    
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

# Function to cleanup auxiliary files (if any)
def cleanup_auxiliary_files():
    for ext in ['.aux', '.log', '.out', '.toc']:
        for file in folder.glob(f"*{ext}"):
            file.unlink(missing_ok=True)

# === STREAMLIT INTERFACE ===

st.title("📄 AutoLaTeX Compiler")

st.markdown("Upload a `.tex` or `.txt` file containing a complete LaTeX structure to compile.")

# Upload LaTeX file
uploaded_file = st.file_uploader("Choose a LaTeX file", type=["tex", "txt"])

if uploaded_file is not None:
    temp_path = folder / uploaded_file.name
    with open(temp_path, 'wb') as f:
        f.write(uploaded_file.read())
    st.success(f"✅ File saved: {uploaded_file.name}")

    # Check if file has LaTeX preamble and compile
    if st.button("🚀 Compile the file"):
        if not has_latex_preamble(temp_path):
            st.warning("⚠️ The file does not contain a valid LaTeX preamble.")
        else:
            latex_content = temp_path.read_text()
            pdf_content = compile_latex_online(latex_content)
            if pdf_content:
                st.success(f"✅ PDF generated: {uploaded_file.name}")
                st.download_button("⬇️ Download PDF", pdf_content, file_name=f"{uploaded_file.name}.pdf")
                st.components.v1.iframe(pdf_content, height=600)
                cleanup_auxiliary_files()
            else:
                st.error("❌ Compilation failed.")
