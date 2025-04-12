import streamlit as st
import os
import requests
from pathlib import Path
from typing import Tuple, Optional, List
import time

# Page config
st.set_page_config(page_title="📝 Online LaTeX Compiler", layout="centered")

# Working directory for temporary files
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

def has_latex_preamble(filepath: Path) -> bool:
    """
    Check if file contains LaTeX preamble.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return any('\\documentclass' in line for line in f)
    except (IOError, UnicodeDecodeError):
        return False

def compile_latex_online(filename: str, output_dir: Optional[Path] = None) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file to PDF using LaTeX Online API and save to output directory.
    
    Args:
        filename (str): Name of the file to compile.
        output_dir (Optional[Path]): Directory to save the PDF (defaults to WORKING_DIR).
    
    Returns:
        Tuple[Optional[Path], str]: Path to generated PDF (or None) and logs.
    """
    input_path = WORKING_DIR / filename
    logs = ""

    # Validate file type
    if filename.lower().endswith('.txt') and not has_latex_preamble(input_path):
        return None, f"⏩ Skipped: {filename} (no LaTeX preamble detected)"

    # Read LaTeX content
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            latex_content = f.read()
    except Exception as e:
        return None, f"❌ Failed to read {filename}: {str(e)}"

    # Compile using LaTeX Online API
    api_url = "https://latexonline.cc/compile"
    payload = {
        "text": latex_content,
        "command": "pdflatex",  # Use pdflatex engine
        "filename": filename
    }

    try:
        response = requests.post(api_url, json=payload, timeout=60)
        if response.status_code == 200 and response.headers.get('content-type') == 'application/pdf':
            # Save PDF
            pdf_name = f"{input_path.stem}.pdf"
            pdf_path = (output_dir or WORKING_DIR) / pdf_name
            pdf_path.write_bytes(response.content)
            logs = "✅ Compilation successful via LaTeX Online."
            return pdf_path, logs
        else:
            logs = f"❌ Compilation failed: {response.text}"
            return None, logs
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {filename}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {filename}: {str(e)}"

# Streamlit UI
st.title("📝 Online LaTeX Compiler")
st.markdown("Upload `.tex` or `.txt` files to compile into PDFs using an online LaTeX compiler.")

# Input for output directory
output_dir_input = st.text_input(
    "Output Directory for PDFs (leave blank to use temporary storage)",
    placeholder="e.g., /home/user/docs",
    help="Enter a folder to save PDFs (server-side; downloads always available)."
)

# Validate output directory (server-side)
output_dir = None
if output_dir_input:
    try:
        output_dir = Path(output_dir_input).resolve()
        if not output_dir.is_dir():
            st.error(f"❌ Invalid directory: {output_dir_input}. Using temporary storage.")
            output_dir = None
    except OSError as e:
        st.error(f"❌ Error accessing directory {output_dir_input}: {str(e)}. Using temporary storage.")
        output_dir = None

# File uploader
uploaded_files = st.file_uploader(
    "Drop your files here:",
    type=["tex", "txt"],
    accept_multiple_files=True,
    help="Maximum file size: 10MB"
)

# Store uploaded file names
if "uploaded_filenames" not in st.session_state:
    st.session_state.uploaded_filenames = []

if uploaded_files:
    st.session_state.uploaded_filenames = []
    for file in uploaded_files:
        if file.size > 10_000_000:  # 10MB limit
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        try:
            file_path.write_bytes(file.getbuffer())
            st.session_state.uploaded_filenames.append(file.name)
        except OSError as e:
            st.error(f"❌ Failed to save {file.name}: {str(e)}")
            continue
    if st.session_state.uploaded_filenames:
        st.success(f"✅ {len(st.session_state.uploaded_filenames)} file(s) uploaded successfully.")

# Display uploaded files and PDFs
if st.session_state.uploaded_filenames:
    st.subheader("📂 Uploaded Files")
    
    for filename in sorted(st.session_state.uploaded_filenames):
        file_path = WORKING_DIR / filename
        pdf_dir = output_dir if output_dir else WORKING_DIR
        pdf_path = pdf_dir / f"{Path(filename).stem}.pdf"
        
        st.markdown(f"**{filename}**")
        
        # Check for existing PDF
        if pdf_path.exists():
            st.success(f"✅ PDF found: {pdf_path.name}")
            st.download_button(
                label=f"📥 Download {pdf_path.name}",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                key=f"download_{filename}_{str(pdf_path.stat().st_mtime)}"
            )
        else:
            st.info(f"ℹ️ No PDF found for {filename}. Compile to generate one.")
        
        # Compile option
        if st.button(f"📄 Compile {filename}", key=f"compile_{filename}"):
            with st.spinner(f"Compiling {filename}..."):
                pdf_path, logs = compile_latex_online(filename, output_dir)
                
                if pdf_path and pdf_path.exists():
                    st.success(f"✅ PDF generated: {pdf_path.name}")
                    st.download_button(
                        label=f"📥 Download {pdf_path.name}",
                        data=pdf_path.read_bytes(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"download_new_{filename}_{str(pdf_path.stat().st_mtime)}"
                    )
                else:
                    st.error("❌ Compilation failed.")
                
                if logs:
                    with st.expander("🧾 View Compilation Logs"):
                        st.text(logs)
else:
    st.info("ℹ️ Upload files to start compiling.")


