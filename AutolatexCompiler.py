import streamlit as st
import requests
import tempfile
from pathlib import Path

# === CONFIGURATION ===
st.set_page_config(page_title="Online LaTeX Compiler", layout="centered")

# Check if a file contains the LaTeX preamble
def has_latex_preamble(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return '\\documentclass' in content and '\\begin{document}' in content
    except Exception as e:
        st.warning(f"Could not read {filepath}: {e}")
        return False

# Function to compile LaTeX file using the latexweb.net API
def compile_latex_online(filepath: Path):
    url = "https://latexweb.net/api/compile"  # Open API URL for LaTeX compilation
    files = {'file': open(filepath, 'rb')}

    try:
        # Make POST request to API
        response = requests.post(url, files=files)
        response.raise_for_status()

        # Parse the PDF URL from the response
        pdf_url = response.json().get('pdf_url')  # Assuming the API returns a URL to the generated PDF
        return pdf_url
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error during LaTeX compilation: {e}")
        return None

# === INTERFACE STREAMLIT ===

st.title("📄 Online LaTeX Compiler")

st.markdown("Upload a `.tex` or `.txt` file containing LaTeX structure to compile it into a PDF.")

uploaded_file = st.file_uploader("Choose a LaTeX file", type=["tex", "txt"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tex") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_path = Path(tmp_file.name)

    st.success(f"✅ File uploaded: {uploaded_file.name}")

    # Check if the file contains a LaTeX preamble
    if uploaded_file.name.lower().endswith('.txt') and not has_latex_preamble(temp_path):
        st.error("❌ The `.txt` file does not contain a valid LaTeX preamble. Please add `\\documentclass` and `\\begin{document}`.")
    else:
        if st.button("🚀 Compile the file"):
            pdf_url = compile_latex_online(temp_path)
            if pdf_url:
                st.success("✅ PDF compiled successfully!")
                st.markdown(f"[⬇️ Download PDF]({pdf_url})")
                st.components.v1.iframe(pdf_url, height=600)
            else:
                st.error("❌ LaTeX compilation failed. Please check your file and try again.")

    # Clean up temporary files
    if temp_path.exists():
        temp_path.unlink(missing_ok=True)
