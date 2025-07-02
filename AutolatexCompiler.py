
import os
st.write("os.getcwd():", os.getcwd())
st.write("os.getlogin():", os.getlogin())
st.write("Path exists:", os.path.exists(r"C:\Users\pc\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"))
st.write("Is file:", os.path.isfile(r"C:\Users\pc\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"))




import streamlit as st
import os
import subprocess
import shutil
import requests
from pathlib import Path
from typing import Tuple, Optional, List
import urllib.parse
import platform
import time

# Page configuration
st.set_page_config(page_title="📝 LaTeX Compiler", layout="centered")

# Working directory for temporary files
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

def is_valid_pdflatex_path(pdflatex_path: str) -> Tuple[bool, str]:
    """
    Validate if the provided pdflatex path points to an executable file.
    
    Args:
        pdflatex_path (str): Path to pdflatex executable.
    
    Returns:
        Tuple[bool, str]: (True if valid, success/error message).
    """
    if not pdflatex_path:
        return False, "No pdflatex path provided."
    
    try:
        # Normalize path for Windows
        if platform.system() == "Windows":
            pdflatex_path = pdflatex_path.replace('/', '\\').replace('\\\\', '\\')
        
        path_obj = Path(pdflatex_path)
        st.info(f"Testing pdflatex path: {path_obj}")
        
        # Check file existence with os.path for reliability
        if not os.path.isfile(str(path_obj)):
            st.warning(f"os.path.isfile reports file missing: {path_obj}")
            # Try common MiKTeX path variations
            possible_paths = [
                str(path_obj).replace('MiKTeX', 'miktex').replace('miktex', 'MiKTeX'),
                str(path_obj).replace('miktex', 'MiKTeX'),
                str(path_obj).replace('MiKTeX', 'miktex'),
                str(path_obj).replace('AppData\\Local\\Programs', 'Program Files'),
                str(path_obj).replace('AppData\\Local\\Programs', 'Program Files (x86)')
            ]
            for alt_path in possible_paths:
                alt_path_obj = Path(alt_path)
                if os.path.isfile(str(alt_path_obj)):
                    path_obj = alt_path_obj
                    st.info(f"Found file with adjusted path: {path_obj}")
                    break
            else:
                return False, f"Path does not point to a file: {pdflatex_path}. Tried: {', '.join(possible_paths)}"
        
        # Test pdflatex executable
        cmd = [str(path_obj), "--version"]
        st.info(f"Running command: {cmd}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and "pdfTeX" in result.stdout:
            return True, f"Valid pdflatex path: {path_obj}"
        return False, f"Invalid pdflatex executable. Command: {cmd}, Return code: {result.returncode}, Output: {result.stdout[:100]}..."
    except FileNotFoundError:
        return False, f"File not found: {pdflatex_path}"
    except PermissionError:
        return False, f"Permission denied: {pdflatex_path}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout while validating: {pdflatex_path}"
    except Exception as e:
        return False, f"Error validating path: {str(e)}"

def has_latex_preamble(filepath: Path) -> bool:
    """
    Check if file contains a LaTeX preamble.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return any('\\documentclass' in line for line in f)
    except Exception:
        return False

def compile_latex_file(filename: str, output_dir: Optional[Path], pdflatex_path: Optional[str]) -> Tuple[Optional[Path], str]:
    """
    Compile a LaTeX file to PDF using local pdflatex.
    
    Args:
        filename (str): Name of the file to compile.
        output_dir (Optional[Path]): Directory to save the PDF.
        pdflatex_path (Optional[str]): Path to pdflatex executable.
    
    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and logs.
    """
    input_path = WORKING_DIR / filename
    temp_pdf = WORKING_DIR / f"{Path(filename).stem}.pdf"
    
    # Convert .txt to .tex if needed
    if filename.lower().endswith('.txt'):
        if not has_latex_preamble(input_path):
            return None, f"⏩ Skipped: {filename} (no LaTeX preamble)"
        tex_path = WORKING_DIR / f"{Path(filename).stem}.tex"
        try:
            input_path.rename(tex_path)
            input_path = tex_path
        except OSError as e:
            return None, f"❌ Failed to rename {filename}: {str(e)}"

    # Determine pdflatex command
    if pdflatex_path:
        is_valid, message = is_valid_pdflatex_path(pdflatex_path)
        if not is_valid:
            return None, f"❌ Invalid pdflatex path: {message}"
        pdflatex_cmd = str(pdflatex_path)
    else:
        pdflatex_cmd = shutil.which("pdflatex")
        if not pdflatex_cmd:
            return None, "❌ pdflatex not found in system PATH."

    try:
        result = subprocess.run(
            [
                pdflatex_cmd,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={WORKING_DIR}",
                str(input_path)
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        if temp_pdf.exists():
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{Path(filename).stem}.pdf"
                try:
                    shutil.move(str(temp_pdf), str(final_pdf))
                    return final_pdf, result.stdout
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}")
                    return temp_pdf, result.stdout
            return temp_pdf, result.stdout
        return None, f"❌ PDF not generated for {filename}"
    except subprocess.TimeoutExpired:
        return None, f"❌ Compilation timed out for {filename}"
    except subprocess.CalledProcessError as e:
        return None, f"❌ Compilation error for {filename}:\n{e.stdout}\n{e.stderr}"
    except Exception as e:
        return None, f"❌ Compilation error for {filename}: {str(e)}"

def cleanup_auxiliary_files(filenames: List[str]) -> bool:
    """
    Remove auxiliary LaTeX files.
    
    Args:
        filenames (List[str]): List of base filenames to clean.
    
    Returns:
        bool: True if cleanup successful, False otherwise.
    """
    extensions = {".aux", ".log", ".out", ".toc", ".synctex.gz", ".nav", ".snm", ".tex"}
    success = True
    
    for filename in filenames:
        base_name = Path(filename).stem
        for ext in extensions:
            aux_file = WORKING_DIR / f"{base_name}{ext}"
            if aux_file.is_file():
                try:
                    aux_file.unlink()
                except OSError as e:
                    st.warning(f"⚠️ Failed to delete {aux_file.name}: {str(e)}")
                    success = False
    return success

def compile_latex_from_github(repo_url: str, file_path: str, output_dir: Optional[Path]) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file from a GitHub repository using LaTeX.Online.
    
    Args:
        repo_url (str): GitHub repository URL.
        file_path (str): Path to the .tex file in the repository.
        output_dir (Optional[Path]): Directory to save the PDF.
    
    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and logs.
    """
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, "❌ File path must be a .tex file."

    temp_pdf = WORKING_DIR / f"{Path(file_path).stem}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    try:
        response = requests.get(api_url, headers={'Accept': 'application/pdf'}, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{Path(file_path).stem}.pdf"
                try:
                    temp_pdf.rename(final_pdf)
                    return final_pdf, "✅ Compilation successful"
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}")
                    return temp_pdf, "✅ Compilation successful"
            return temp_pdf, "✅ Compilation successful"
        return None, f"❌ Compilation error: Status {response.status_code}\n{response.text[:100]}..."
    except requests.Timeout:
        return None, "❌ Compilation timed out."
    except requests.RequestException as e:
        return None, f"❌ Network error: {str(e)}"

# Streamlit UI
st.title("📝 LaTeX Compiler")
st.markdown("Compile LaTeX files to PDFs locally or from GitHub. Save PDFs to a specified folder or the working directory.")

# Configuration
st.subheader("⚙️ Settings")
pdflatex_path = st.text_input(
    "pdflatex Path (optional)",
    placeholder="e.g., C:/Users/pc/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
    help="Enter the full path to pdflatex.exe. Leave blank to use system PATH."
)

# Validate pdflatex path
if pdflatex_path:
    is_valid, message = is_valid_pdflatex_path(pdflatex_path)
    if is_valid:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")

# Output directory
output_dir_input = st.text_input(
    "Output Directory (optional)",
    placeholder="e.g., C:/Users/pc/Documents",
    help="Folder to save PDFs. Leave blank to use working directory."
)
output_dir = None
if output_dir_input:
    try:
        output_dir = Path(output_dir_input)
        if not output_dir.is_dir():
            st.error(f"❌ Invalid directory: {output_dir_input}")
            output_dir = None
    except Exception as e:
        st.error(f"❌ Error accessing directory: {str(e)}")
        output_dir = None

# GitHub compilation
st.subheader("📦 Compile from GitHub")
github_repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="e.g., https://github.com/username/repo"
)
github_file_path = st.text_input(
    "Main .tex File Path",
    placeholder="e.g., main.tex"
)

if github_repo_url and github_file_path:
    if st.button("📄 Compile from GitHub"):
        with st.spinner("Compiling from GitHub..."):
            pdf_path, logs = compile_latex_from_github(github_repo_url, github_file_path, output_dir)
            if pdf_path and pdf_path.exists():
                st.success(f"✅ PDF generated: {pdf_path}")
                st.download_button(
                    label=f"📥 Download {pdf_path.name}",
                    data=pdf_path.read_bytes(),
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    key=f"download_github_{pdf_path.name}_{str(time.time())}"
                )
            else:
                st.error("❌ Compilation failed.")
            if logs:
                with st.expander("🧾 Logs"):
                    st.text(logs)

# Local file upload
st.subheader("📤 Upload Files")
uploaded_files = st.file_uploader(
    "Upload .tex or .txt files",
    type=["tex", "txt"],
    accept_multiple_files=True,
    help="Max size: 10MB"
)

# Store uploaded files
if "uploaded_filenames" not in st.session_state:
    st.session_state.uploaded_filenames = []

if uploaded_files:
    st.session_state.uploaded_filenames = []
    compiled_files = []
    for file in uploaded_files:
        if file.size > 10_000_000:
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        try:
            file_path.write_bytes(file.getbuffer())
            st.session_state.uploaded_filenames.append(file.name)
            compiled_files.append(file.name)
        except Exception as e:
            st.error(f"❌ Failed to save {file.name}: {str(e)}")
    if st.session_state.uploaded_filenames:
        st.success(f"✅ {len(st.session_state.uploaded_filenames)} file(s) uploaded")

# Display and compile uploaded files
if st.session_state.uploaded_filenames:
    st.subheader("📂 Files")
    compiled_files = []
    
    for filename in sorted(st.session_state.uploaded_filenames):
        file_path = WORKING_DIR / filename
        pdf_dir = output_dir if output_dir else WORKING_DIR
        pdf_path = pdf_dir / f"{Path(filename).stem}.pdf"
        
        st.markdown(f"**{filename}**")
        if pdf_path.exists():
            st.success(f"✅ PDF found: {pdf_path}")
            st.download_button(
                label=f"📥 Download {pdf_path.name}",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                key=f"download_{filename}_{str(time.time())}"
            )
        else:
            st.info("ℹ️ No PDF found. Compile to generate.")
        
        if st.button(f"📄 Compile {filename}", key=f"compile_{filename}"):
            if not pdflatex_path and not shutil.which("pdflatex"):
                st.error("❌ pdflatex not found in system PATH.")
            elif not file_path.exists():
                st.error(f"❌ File {filename} not found.")
            else:
                with st.spinner(f"Compiling {filename}..."):
                    pdf_path, logs = compile_latex_file(filename, output_dir, pdflatex_path)
                    if pdf_path and pdf_path.exists():
                        st.success(f"✅ PDF generated: {pdf_path}")
                        st.download_button(
                            label=f"📥 Download {pdf_path.name}",
                            data=pdf_path.read_bytes(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"download_new_{filename}_{str(time.time())}"
                        )
                        compiled_files.append(filename)
                    else:
                        st.error("❌ Compilation failed.")
                    if logs:
                        with st.expander("🧾 Logs"):
                            st.text(logs)
    
    if compiled_files and st.button("🧹 Clean Up"):
        with st.spinner("Cleaning up..."):
            if cleanup_auxiliary_files(compiled_files):
                st.info("🧹 Cleanup successful.")
            else:
                st.warning("⚠️ Cleanup failed. Check warnings.")

if not st.session_state.uploaded_filenames and not (github_repo_url and github_file_path):
    st.info("ℹ️ Upload files or enter a GitHub URL to start.")
