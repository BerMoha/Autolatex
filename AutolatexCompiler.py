import streamlit as st
import os
import requests
from pathlib import Path
from typing import Tuple, Optional, List
import warnings
import time

# Suppress Streamlit warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Page config
st.set_page_config(page_title="📝 LaTeX Compiler", layout="centered")

# Use Path for cross-platform compatibility
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

def compile_latex_file(filename: str, output_dir: Optional[Path] = None) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file to PDF using LaTeX.Online API and save PDF to the specified output directory.
    
    Args:
        filename (str): Name of the file to compile.
        output_dir (Optional[Path]): Directory to save the PDF (defaults to WORKING_DIR).
    
    Returns:
        Tuple[Optional[Path], str]: Path to generated PDF (or None) and compilation logs.
    """
    input_path = WORKING_DIR / filename
    
    # Validate file type and convert if needed
    if filename.lower().endswith('.txt'):
        if not has_latex_preamble(input_path):
            return None, f"⏩ Skipped: {filename} (no LaTeX preamble detected)"
        tex_name = filename.replace('.txt', '.tex')
        tex_path = WORKING_DIR / tex_name
        try:
            input_path.rename(tex_path)
            input_path = tex_path
        except OSError as e:
            return None, f"❌ Failed to rename {filename}: {str(e)}"

    # Prepare output path
    temp_pdf = WORKING_DIR / f"{input_path.stem}.pdf"

    # Read file content
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            tex_content = f.read()
    except OSError as e:
        return None, f"❌ Failed to read {filename}: {str(e)}"

    # Send to LaTeX.Online API
    api_url = "https://latexonline.cc/compile?text"
    try:
        response = requests.post(api_url, data=tex_content.encode('utf-8'), timeout=60)
        
        if response.status_code == 200:
            # Save PDF
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
            
            # Move PDF to output_dir if specified
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{input_path.stem}.pdf"
                try:
                    temp_pdf.rename(final_pdf)
                    return final_pdf, "✅ Compilation successful"
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}. Keeping in {WORKING_DIR}")
                    return temp_pdf, "✅ Compilation successful"
            return temp_pdf, "✅ Compilation successful"
        else:
            return None, f"❌ Compilation error for {filename}:\n{response.text}"
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {filename}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {filename}: {str(e)}"

# Streamlit UI
st.title("📝 LaTeX Compiler")
st.markdown("Upload your `.tex` or `.txt` files to compile into PDFs using LaTeX.Online. PDFs will be saved to the specified folder or the working directory.")

# Input for output directory
output_dir_input = st.text_input(
    "Output Directory for PDFs (leave blank to use working directory)",
    placeholder="e.g., C:/Users/YourName/Documents or /home/user/docs",
    help="Enter the folder where your .tex/.txt files are located to save PDFs there."
)

# Validate output directory
output_dir = None
if output_dir_input:
    try:
        output_dir = Path(output_dir_input).resolve()
        if not output_dir.is_dir():
            st.error(f"❌ Invalid directory: {output_dir_input}. Using working directory instead.")
            output_dir = None
    except OSError as e:
        st.error(f"❌ Error accessing directory {output_dir_input}: {str(e)}. Using working directory instead.")
        output_dir = None

# File uploader with size limit
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
    st.session_state.uploaded_filenames = []  # Reset for new uploads
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
    else:
        st.warning("⚠️ No files were uploaded successfully.")

# Display uploaded files and PDFs
if st.session_state.uploaded_filenames:
    st.subheader("📂 Uploaded Files")
    
    for filename in sorted(st.session_state.uploaded_filenames):
        file_path = WORKING_DIR / filename
        # Check PDF in output_dir if specified, else WORKING_DIR
        pdf_dir = output_dir if output_dir else WORKING_DIR
        pdf_path = pdf_dir / f"{Path(filename).stem}.pdf"
        
        st.markdown(f"**{filename}**")
        
        # Check for existing PDF
        if pdf_path.exists():
            st.success(f"✅ PDF found: {pdf_path}")
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
                pdf_path, logs = compile_latex_file(filename, output_dir)
                
                if pdf_path and pdf_path.exists():
                    st.success(f"✅ PDF generated: {pdf_path}")
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


