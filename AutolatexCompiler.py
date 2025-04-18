import streamlit as st
import requests
from pathlib import Path
from typing import Tuple, Optional, List
import warnings
import time
import urllib.parse

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

    # Debug: Log LaTeX content
    st.write(f"DEBUG: Sending LaTeX content for {filename}:\n{tex_content[:500]}...")  # Limit to first 500 chars

    # Send to LaTeX.Online API
    api_url = "https://latexonline.cc/compile?command=pdflatex"
    headers = {'Content-Type': 'text/plain; charset=utf-8'}
    try:
        response = requests.post(api_url, data=tex_content.encode('utf-8'), headers=headers, timeout=60)
        st.write(f"DEBUG: API Response Status: {response.status_code}")
        st.write(f"DEBUG: API Response Text: {response.text[:1000]}...")  # Limit for readability
        
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
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
            return None, f"❌ Compilation error for {filename}:\nStatus: {response.status_code}\n{response.text}"
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {filename}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {filename}: {str(e)}"

def compile_latex_from_github(repo_url: str, file_path: str, output_dir: Optional[Path] = None) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file from a GitHub repository using LaTeX.Online's Git endpoint.
    
    Args:
        repo_url (str): GitHub repository URL (e.g., https://github.com/username/repo).
        file_path (str): Path to the main .tex file in the repository (e.g., path/to/file.tex).
        output_dir (Optional[Path]): Directory to save the PDF (defaults to WORKING_DIR).
    
    Returns:
        Tuple[Optional[Path], str]: Path to generated PDF (or None) and compilation logs.
    """
    # Validate inputs
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub repository URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, "❌ File path must point to a .tex file"

    # Prepare output path
    temp_pdf = WORKING_DIR / f"{Path(file_path).stem}.pdf"

    # Construct LaTeX.Online Git API URL
    # Convert repo_url to raw Git URL (e.g., https://github.com/username/repo -> https://github.com/username/repo.git)
    git_url = repo_url.rstrip('/') + '.git'
    # Encode file path for URL
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    # Debug: Log API URL
    st.write(f"DEBUG: Git API URL: {api_url}")

    # Send request to LaTeX.Online
    headers = {'Accept': 'application/pdf'}
    try:
        response = requests.get(api_url, headers=headers, timeout=60)
        st.write(f"DEBUG: Git API Response Status: {response.status_code}")
        st.write(f"DEBUG: Git API Response Text: {response.text[:1000]}...")  # Limit for readability

        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            # Save PDF
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
            
            # Move PDF to output_dir if specified
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{Path(file_path).stem}.pdf"
                try:
                    temp_pdf.rename(final_pdf)
                    return final_pdf, "✅ Compilation successful"
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}. Keeping in {WORKING_DIR}")
                    return temp_pdf, "✅ Compilation successful"
            return temp_pdf, "✅ Compilation successful"
        else:
            return None, f"❌ Compilation error for {file_path}:\nStatus: {response.status_code}\n{response.text}"
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {file_path}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {file_path}: {str(e)}"

# Streamlit UI
st.title("📝 LaTeX Compiler")
st.markdown("""
Upload your `.tex` or `.txt` files or provide a GitHub repository URL to compile into PDFs using LaTeX.Online.
PDFs will be saved to the specified folder or the working directory.
""")

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

# GitHub repository input
st.subheader("📦 Compile from GitHub")
github_repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="e.g., https://github.com/username/repo",
    help="Enter the GitHub repository URL containing your LaTeX project."
)
github_file_path = st.text_input(
    "Main .tex File Path",
    placeholder="e.g., path/to/Fourier VS Dunkl.tex",
    help="Enter the path to the main .tex file in the repository."
)

# Compile from GitHub
if github_repo_url and github_file_path:
    if st.button("📄 Compile from GitHub", key="compile_github"):
        with st.spinner(f"Compiling {github_file_path} from GitHub..."):
            pdf_path, logs = compile_latex_from_github(github_repo_url, github_file_path, output_dir)
            
            if pdf_path and pdf_path.exists():
                st.success(f"✅ PDF generated: {pdf_path}")
                st.download_button(
                    label=f"📥 Download {pdf_path.name}",
                    data=pdf_path.read_bytes(),
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    key=f"download_github_{pdf_path.name}_{str(pdf_path.stat().st_mtime)}"
                )
            else:
                st.error("❌ Compilation failed.")
            
            if logs:
                with st.expander("🧾 View Compilation Logs"):
                    st.text(logs)

# File uploader with size limit
st.subheader("📤 Upload Local Files")
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
    st.info("ℹ️ Upload files or enter a GitHub repository to start compiling.")
