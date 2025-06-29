import streamlit as st
import os
import subprocess
import shutil
import requests
import warnings
import time
from pathlib import Path
from typing import Tuple, Optional, List
import urllib.parse
import platform

# Suppress Streamlit warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Page config
st.set_page_config(page_title="📝 LaTeX Compiler", layout="centered")

# Use Path for cross-platform compatibility
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
    try:
        # Normalize path for Windows
        if platform.system() == "Windows":
            pdflatex_path = pdflatex_path.replace('/', '\\').replace('\\\\', '\\')
        
        # Create Path object
        path_obj = Path(pdflatex_path)
        
        # Log the path being tested
        st.info(f"Testing pdflatex path: {path_obj}")
        
        # Check if path exists as a file without resolving
        if not path_obj.is_file():
            # Try alternative case variations for MiKTeX
            possible_paths = [
                str(path_obj).replace('MiKTeX', 'miktex').replace('miktex', 'MiKTeX'),
                str(path_obj).replace('miktex', 'MiKTeX'),
                str(path_obj).replace('MiKTeX', 'miktex')
            ]
            for alt_path in possible_paths:
                alt_path_obj = Path(alt_path)
                if alt_path_obj.is_file():
                    path_obj = alt_path_obj
                    st.info(f"Found file with adjusted case: {path_obj}")
                    break
            else:
                return False, f"Path does not point to a file: {pdflatex_path}"
        
        # Test if the path points to a valid pdflatex executable
        cmd = [str(path_obj), "--version"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and "pdfTeX" in result.stdout:
            return True, f"Valid pdflatex path: {path_obj}"
        else:
            return False, f"Invalid pdflatex executable. Command: {cmd}, Return code: {result.returncode}, Output: {result.stdout[:100]}..."
    except FileNotFoundError:
        return False, f"File not found: {pdflatex_path}"
    except PermissionError:
        return False, f"Permission denied: {pdflatex_path}"
    except subprocess.TimeoutExpired:
        return False, f"Timeout while validating: {pdflatex_path}"
    except subprocess.SubprocessError as e:
        return False, f"Subprocess error: {str(e)}"

def has_latex_preamble(filepath: Path) -> bool:
    """
    Check if file contains LaTeX preamble.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return any('\\documentclass' in line for line in f)
    except (IOError, UnicodeDecodeError):
        return False

def compile_latex_file(filename: str, output_dir: Optional[Path] = None, pdflatex_path: Optional[str] = None) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file to PDF using local pdflatex and save PDF to the specified output directory.
    
    Args:
        filename (str): Name of the file to compile.
        output_dir (Optional[Path]): Directory to save the PDF (defaults to WORKING_DIR).
        pdflatex_path (Optional[str]): Path to pdflatex executable (if provided).
    
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

    # Compile in WORKING_DIR
    temp_pdf = WORKING_DIR / f"{input_path.stem}.pdf"

    # Determine pdflatex executable
    if pdflatex_path:
        is_valid, message = is_valid_pdflatex_path(pdflatex_path)
        if is_valid:
            pdflatex_cmd = str(pdflatex_path)
        else:
            return None, f"❌ Invalid pdflatex path: {message}"
    else:
        pdflatex_cmd = shutil.which("pdflatex")
        if not pdflatex_cmd:
            return None, "❌ pdflatex not found in system PATH. Please provide a valid pdflatex path."

    try:
        # Run pdflatex with timeout
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
        # Verify PDF was generated
        if temp_pdf.exists():
            # Move PDF to output_dir if specified, else keep in WORKING_DIR
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{input_path.stem}.pdf"
                try:
                    shutil.move(str(temp_pdf), str(final_pdf))
                    return final_pdf, result.stdout
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}. Keeping in {WORKING_DIR}")
                    return temp_pdf, result.stdout
            return temp_pdf, result.stdout
        else:
            return None, f"❌ PDF not generated for {filename}"
    except subprocess.TimeoutExpired:
        return None, f"❌ Compilation timed out for {filename}"
    except subprocess.CalledProcessError as e:
        return None, f"❌ Compilation error for {filename}:\n{e.stdout}\n{e.stderr}"

def cleanup_auxiliary_files(filenames: List[str]) -> bool:
    """
    Remove auxiliary LaTeX files generated by the specified files from WORKING_DIR.
    
    Args:
        filenames (List[str]): List of base filenames (without extensions) to clean up.
    
    Returns:
        bool: True if all files were deleted successfully, False if any errors occurred.
    """
    auxiliary_extensions = {".aux", ".log", ".out", ".toc", ".synctex.gz", ".nav", ".snm", ".tex"}
    success = True
    
    for filename in filenames:
        base_name = Path(filename).stem
        for ext in auxiliary_extensions:
            aux_file = WORKING_DIR / f"{base_name}{ext}"
            if aux_file.is_file():
                for _ in range(3):  # Retry up to 3 times
                    try:
                        aux_file.unlink()
                        break
                    except OSError as e:
                        st.warning(f"⚠️ Attempting to delete {aux_file.name}: {str(e)}")
                        success = False
                        time.sleep(0.5)  # Wait before retrying
                else:
                    st.error(f"❌ Failed to delete {aux_file.name} after retries")
                    success = False
    
    return success

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
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub repository URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, "❌ File path must point to a .tex file"

    temp_pdf = WORKING_DIR / f"{Path(file_path).stem}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    headers = {'Accept': 'application/pdf'}
    try:
        response = requests.get(api_url, headers=headers, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
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
Compile LaTeX files into PDFs. Upload local `.tex` or `.txt` files to compile using local pdflatex, or provide a GitHub repository URL to compile using LaTeX.Online.
PDFs will be saved to the specified folder or the working directory.
""")

# Input for pdflatex path
st.subheader("⚙️ Configuration")
pdflatex_path = st.text_input(
    "pdflatex Path (optional)",
    placeholder="e.g., C:/Users/pc/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
    help="Enter the full path to the pdflatex executable. Use forward (/) or backslashes (\\). Leave blank to use pdflatex from your system PATH."
)

# Validate pdflatex path if provided
if pdflatex_path:
    is_valid, message = is_valid_pdflatex_path(pdflatex_path)
    if is_valid:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")

# Input for output directory
output_dir_input = st.text_input(
    "Output Directory for PDFs (leave blank to use working directory)",
    placeholder="e.g., C:/Users/pc/Documents",
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
    compiled_files = []
    for file in uploaded_files:
        if file.size > 10_000_000:  # 10MB limit
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        try:
            file_path.write_bytes(file.getbuffer())
            st.session_state.uploaded_filenames.append(file.name)
            compiled_files.append(file.name)
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
    compiled_files = []
    
    for filename in sorted(st.session_state.uploaded_filenames):
        file_path = WORKING_DIR / filename
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
            if not pdflatex_path and not shutil.which("pdflatex"):
                st.error("❌ pdflatex not found in system PATH. Please provide a valid pdflatex path.")
            elif not file_path.exists():
                st.error(f"❌ File {filename} not found in working directory.")
            else:
                with st.spinner(f"Compiling {filename}..."):
                    pdf_path, logs = compile_latex_file(filename, output_dir, pdflatex_path)
                    
                    if pdf_path and pdf_path.exists():
                        st.success(f"✅ PDF generated: {pdf_path}")
                        st.download_button(
                            label=f"📥 Download {pdf_path.name  return None, "❌ Invalid GitHub repository URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, "❌ File path must point to a .tex file"

    temp_pdf = WORKING_DIR / f"{Path(file_path).stem}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    headers = {'Accept': 'application/pdf'}
    try:
        response = requests.get(api_url, headers=headers, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
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
Compile LaTeX files into PDFs. Upload local `.tex` or `.txt` files to compile using local pdflatex, or provide a GitHub repository URL to compile using LaTeX.Online.
PDFs will be saved to the specified folder or the working directory.
""")

# Input for pdflatex path
st.subheader("⚙️ Configuration")
pdflatex_path = st.text_input(
    "pdflatex Path (optional)",
    placeholder="e.g., C:/Users/pc/AppData/Local/Programs/MiKTeX/miktex/bin/x64/pdflatex.exe",
    help="Enter the full path to the pdflatex executable. Use forward (/) or backslashes (\\). Leave blank to use pdflatex from your system PATH."
)

# Validate pdflatex path if provided
if pdflatex_path:
    is_valid, message = is_valid_pdflatex_path(pdflatex_path)
    if is_valid:
        st.success(f"✅ {message}")
    else:
        st.error(f"❌ {message}")

# Input for output directory
output_dir_input = st.text_input(
    "Output Directory for PDFs (leave blank to use working directory)",
    placeholder="e.g., C:/Users/pc/Documents",
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
    compiled_files = []
    for file in uploaded_files:
        if file.size > 10_000_000:  # 10MB limit
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        try:
            file_path.write_bytes(file.getbuffer())
            st.session_state.uploaded_filenames.append(file.name)
            compiled_files.append(file.name)
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
    compiled_files = []
    
    for filename in sorted(st.session_state.uploaded_filenames):
        file_path = WORKING_DIR / filename
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
            if not pdflatex_path and not shutil.which("pdflatex"):
                st.error("❌ pdflatex not found in system PATH. Please provide a valid pdflatex path.")
            elif not file_path.exists():
                st.error(f"❌ File {filename} not found in working directory.")
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
                            key=f"download_new_{filename}_{str(pdf_path.stat().st_mtime)}"
                        )
                        compiled_files.append(filename)
                    else:
                        st.error("❌ Compilation failed.")
                    
                    if logs:
                        with st.expander("🧾 View Compilation Logs"):
                            st.text(logs)
    
    # Cleanup option
    if compiled_files:
        if st.button("🧹 Clean Up Auxiliary Files", key="cleanup_button"):
            with st.spinner("Cleaning up auxiliary files..."):
                if cleanup_auxiliary_files(compiled_files):
                    st.info("🧹 Cleanup of auxiliary files completed successfully.")
                else:
                    st.warning("⚠️ Cleanup completed with some errors. Check warnings above.")
else:
    st.info("ℹ️ Upload files or enter a GitHub repository to start compiling.")
