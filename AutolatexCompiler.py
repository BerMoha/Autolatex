import streamlit as st
import requests
from io import BytesIO

# === CONFIGURATION ===
st.set_page_config(page_title="AutoLaTeX Compiler", layout="centered")

# Function to check if LaTeX content has the preamble
def has_latex_preamble(latex_content):
    return '\\documentclass' in latex_content and '\\begin{document}' in latex_content

# Function to send LaTeX content to QuickLaTeX API for compilation
def compile_latex_online(latex_content):
    url = "https://quicklatex.com/latex3.f"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'formula': latex_content, 
        'fsize': '12', 
        'fcolor': '000000', 
        'bg': 'FFFFFF', 
        'mode': '0'
    }
    
    try:
        # Send POST request to QuickLaTeX
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.content  # PDF content in bytes
        else:
            st.error("❌ LaTeX compilation failed!")
            return None
    except Exception as e:
        st.error(f"❌ Error during API request: {e}")
        return None

# === STREAMLIT INTERFACE ===

st.title("📄 AutoLaTeX Compiler")

st.markdown("Upload a `.tex` or `.txt` file containing a complete LaTeX structure to compile.")

# Upload LaTeX file
uploaded_file = st.file_uploader("Choose a LaTeX file", type=["tex", "txt"])

if uploaded_file is not None:
    # Read uploaded file content
    latex_content = uploaded_file.read().decode('utf-8')

    # Check for LaTeX preamble
    if not has_latex_preamble(latex_content):
        st.warning("⚠️ The file does not contain a valid LaTeX preamble. Please ensure it contains `\\documentclass` and `\\begin{document}`.")
    else:
        # Button to trigger LaTeX compilation
        if st.button("🚀 Compile the file"):
            # Send content to QuickLaTeX API for compilation
            pdf_content = compile_latex_online(latex_content)
            if pdf_content:
                st.success(f"✅ PDF generated successfully!")
                st.download_button("⬇️ Download PDF", pdf_content, file_name="compiled_output.pdf")
                st.components.v1.iframe(pdf_content, height=600)
            else:
                st.error("❌ Failed to compile the LaTeX document.")
