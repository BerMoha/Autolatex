import streamlit as st
import requests
import urllib.parse
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, List
import os
import time

# Page configuration
st.set_page_config(page_title="📝 LaTeX Compiler", layout="centered")

# Working directory for temporary files
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

def check_pdflatex() -> Tuple[bool, str]:
    """
    Check if pdflatex is available for local compilation.

    Returns:
        Tuple[bool, str]: (True if available, message).
    """
    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        return False, ("❌ pdflatex not found. Install MiKTeX (https://miktex.org/download) "
                      "for local compilation or use a custom LaTeX.Online server.")
    try:
        result = subprocess.run(
            [pdflatex_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and "pdfTeX" in result.stdout:
            return True, f"✅ pdflatex found: {pdflatex_path}"
        return False, f"❌ Invalid pdflatex: {result.stdout[:100]}..."
    except Exception as e:
        return False, f"❌ Error checking pdflatex: {str(e)}"

def check_repository_access(repo_url: str, latex_online_url: str) -> Tuple[bool, str]:
    """
    Check if the GitHub repository is accessible via the LaTeX.Online server.

    Args:
        repo_url (str): GitHub repository URL.
        latex_online_url (str): LaTeX.Online server URL.

    Returns:
        Tuple[bool, str]: (True if accessible, message).
    """
    if not repo_url.startswith("https://github.com/"):
        return False, "❌ Invalid GitHub URL. Must start with https://github.com/"
    git_url = repo_url.rstrip('/') + '.git'
    try:
        response = requests.get(f"https://api.github.com/repos/{repo_url.split('github.com/')[1]}", timeout=10)
        if response.status_code == 200:
            if response.json().get("private", True):
                return False, ("❌ Repository is private. Ensure your LaTeX.Online server is configured with a GitHub PAT "
                              "(see https://github.com/aslushnikov/latex-online). Alternatively, use local compilation.")
            return True, "✅ Repository is accessible."
        elif response.status_code == 404:
            return False, "❌ Repository not found. Check the URL."
        return False, f"❌ Failed to access repository: Status {response.status_code}"
    except requests.RequestException as e:
        return False, f"❌ Network error checking repository: {str(e)}"

async def compile_latex_online(latex_online_url: str, repo_url: str, file_path: str, output_dir: Optional[Path]) -> Tuple[Optional[Path], str]:
    """
    Compile a LaTeX file from a GitHub repository using a LaTeX.Online server.

    Args:
        latex_online_url (str): Base URL of the LaTeX.Online server.
        repo_url (str): GitHub repository URL.
        file_path (str): Path to the .tex file in the repository.
        output_dir (Optional[Path]): Directory to save the PDF.

    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and logs.
    """
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, f"❌ File {file_path} must be a .tex file."

    temp_pdf = WORKING_DIR / f"{Path(file_path).stem.replace(' ', '_')}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"{latex_online_url.rstrip('/')}/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    try:
        response = requests.get(api_url, headers={'Accept': 'application/pdf'}, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{Path(file_path).stem.replace(' ', '_')}.pdf"
                try:
                    temp_pdf.rename(final_pdf)
                    return final_pdf, "✅ Compilation successful"
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}")
                    return temp_pdf, "✅ Compilation successful"
            return temp_pdf, "✅ Compilation successful"
        return None, f"❌ Compilation error for {file_path}: Status {response.status_code}\n{response.text[:100]}..."
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {file_path}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {file_path}: {str(e)}"

def compile_latex_local(filename: str, output_dir: Optional[Path]) -> Tuple[Optional[Path], str]:
    """
    Compile a LaTeX file locally using pdflatex.

    Args:
        filename (str): Name of the .tex file.
        output_dir (Optional[Path]): Directory to save the PDF.

    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and logs.
    """
    input_path = WORKING_DIR / filename
    temp_pdf = WORKING_DIR / f"{Path(filename).stem.replace(' ', '_')}.pdf"

    if not input_path.exists():
        return None, f"❌ File {filename} not found in working directory."

    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        return None, "❌ pdflatex not found in system PATH."

    try:
        result = subprocess.run(
            [
                pdflatex_path,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={WORKING_DIR}",
                str(input_path)
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        if temp_pdf.exists():
            if output_dir and output_dir.is_dir():
                final_pdf = output_dir / f"{Path(filename).stem.replace(' ', '_')}.pdf"
                try:
                    shutil.move(str(temp_pdf), str(final_pdf))
                    return final_pdf, result.stdout
                except OSError as e:
                    st.warning(f"⚠️ Failed to move PDF to {output_dir}: {str(e)}")
                    return temp_pdf, result.stdout
            return temp_pdf, result.stdout
        return None, f"❌ PDF not generated for {filename}: {result.stdout[:100]}..."
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
        filenames (List[str]): List of base filenames.

    Returns:
        bool: True if cleanup successful.
    """
    extensions = {".aux", ".log", ".out", ".toc", ".synctex.gz", ".nav", ".snm"}
    success = True
    for filename in filenames:
        base_name = Path(filename).stem.replace(' ', '_')
        for ext in extensions:
            aux_file = WORKING_DIR / f"{base_name}{ext}"
            if aux_file.is_file():
                try:
                    aux_file.unlink()
                except OSError as e:
                    st.warning(f"⚠️ Failed to delete {aux_file.name}: {str(e)}")
                    success = False
    return success

# Streamlit UI
st.title("📝 LaTeX Compiler")
st.markdown("Compile LaTeX files from a private GitHub repository using a self-hosted LaTeX.Online server "
            "(configured with a GitHub PAT) or locally with pdflatex (requires MiKTeX). "
            "Upload .tex files or specify repository and file paths.")

# Configuration
st.subheader("⚙️ Settings")
latex_online_url = st.text_input(
    "LaTeX.Online Server URL",
    placeholder="e.g., http://localhost:3000 or https://latexonline.cc",
    value="https://latexonline.cc",
    help="Use a self-hosted LaTeX.Online server with PAT for private repositories (see https://github.com/aslushnikov/latex-online)."
)
output_dir_input = st.text_input(
    "Output Directory (optional)",
    placeholder="e.g., C:/Users/pc/Desktop/Autolatex",
    value="C:/Users/pc/Desktop/Autolatex",
    help="Local folder to save PDFs."
)
output_dir = None
if output_dir_input:
    output_dir_input = output_dir_input.strip().replace('/', '\\')
    if output_dir_input.lower().startswith(('http://', 'https://')):
        st.error(f"❌ Output directory cannot be a URL: {output_dir_input}")
    else:
        try:
            output_dir = Path(output_dir_input)
            if not os.path.exists(str(output_dir)):
                output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                st.error(f"❌ Path is not a directory: {output_dir_input}")
                output_dir = None
        except Exception as e:
            st.error(f"❌ Error accessing directory {output_dir_input}: {str(e)}")
            output_dir = None

# Check pdflatex availability
is_pdflatex_available, pdflatex_message = check_pdflatex()
if is_pdflatex_available:
    st.success(pdflatex_message)
else:
    st.warning(pdflatex_message)

# Compilation mode
compilation_mode = st.radio(
    "Compilation Mode",
    ["Online (LaTeX.Online)", "Local (pdflatex)"],
    help="Choose 'Online' for a self-hosted LaTeX.Online server with PAT, or 'Local' for pdflatex (requires MiKTeX)."
)

# Online compilation inputs
if compilation_mode == "Online (LaTeX.Online)":
    github_repo_url = st.text_input(
        "GitHub Repository URL",
        placeholder="e.g., https://github.com/BerMoha/Autolatex",
        value="https://github.com/BerMoha/Autolatex"
    )
    if github_repo_url:
        is_accessible, repo_message = check_repository_access(github_repo_url, latex_online_url)
        if is_accessible:
            st.success(repo_message)
        else:
            st.error(repo_message)

# File input
st.subheader("📤 Upload .tex Files")
uploaded_files = st.file_uploader(
    "Upload .tex files",
    type=["tex"],
    accept_multiple_files=True,
    help="Upload .tex files from your local clone (e.g., C:/Users/pc/Desktop/Autolatex)."
)
if "uploaded_filenames" not in st.session_state:
    st.session_state.uploaded_filenames = []
if uploaded_files:
    st.session_state.uploaded_filenames = []
    for file in uploaded_files:
        if file.size > 10_000_000:
            st.error(f"❌ {file.name} exceeds 10MB limit")
            continue
        file_path = WORKING_DIR / file.name
        try:
            file_path.write_bytes(file.getbuffer())
            st.session_state.uploaded_filenames.append(file.name)
        except Exception as e:
            st.error(f"❌ Failed to save {file.name}: {str(e)}")
    if st.session_state.uploaded_filenames:
        st.success(f"✅ {len(st.session_state.uploaded_filenames)} file(s) uploaded")

# Manual file paths
file_paths_input = st.text_input(
    "Main .tex File Paths (comma-separated)",
    placeholder="e.g., Fourier VS Dunkl.tex,chapter1.tex",
    value="Fourier VS Dunkl.tex"
)

# Compile button
if st.session_state.uploaded_filenames or file_paths_input or (compilation_mode == "Online (LaTeX.Online)" and github_repo_url):
    if st.button("📄 Compile Files"):
        file_paths = [fp.strip() for fp in file_paths_input.split(',') if fp.strip()] + st.session_state.uploaded_filenames
        file_paths = list(dict.fromkeys(file_paths))  # Remove duplicates
        if not file_paths:
            st.error("❌ No valid file paths provided.")
        else:
            compiled_files = []
            if compilation_mode == "Local (pdflatex)":
                if not is_pdflatex_available:
                    st.error(f"❌ Cannot compile locally: {pdflatex_message}")
                else:
                    with st.spinner(f"Compiling {len(file_paths)} file(s) locally..."):
                        for file_path in file_paths:
                            st.markdown(f"**{file_path}**")
                            pdf_path, logs = compile_latex_local(file_path, output_dir)
                            if pdf_path and pdf_path.exists():
                                st.success(f"✅ PDF generated: {pdf_path}")
                                st.download_button(
                                    label=f"📥 Download {pdf_path.name}",
                                    data=pdf_path.read_bytes(),
                                    file_name=pdf_path.name,
                                    mime="application/pdf",
                                    key=f"download_{file_path}_{str(time.time())}"
                                )
                                compiled_files.append(file_path)
                            else:
                                st.error(f"❌ Compilation failed for {file_path}")
                            if logs:
                                with st.expander(f"🧾 Logs for {file_path}"):
                                    st.text(logs)
            else:
                if not is_accessible:
                    st.error(f"❌ Cannot compile online: {repo_message}")
                else:
                    with st.spinner(f"Compiling {len(file_paths)} file(s) online..."):
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        tasks = [compile_latex_online(latex_online_url, github_repo_url, file_path, output_dir) for file_path in file_paths]
                        results = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                        loop.close()
                        for i, file_path in enumerate(file_paths):
                            pdf_path, logs = results[i]
                            st.markdown(f"**{file_path}**")
                            if pdf_path and pdf_path.exists():
                                st.success(f"✅ PDF generated: {pdf_path}")
                                st.download_button(
                                    label=f"📥 Download {pdf_path.name}",
                                    data=pdf_path.read_bytes(),
                                    file_name=pdf_path.name,
                                    mime="application/pdf",
                                    key=f"download_{file_path}_{str(time.time())}"
                                )
                                compiled_files.append(file_path)
                            else:
                                st.error(f"❌ Compilation failed for {file_path}")
                            if logs:
                                with st.expander(f"🧾 Logs for {file_path}"):
                                    st.text(logs)

            if compiled_files and st.button("🧹 Clean Up Auxiliary Files"):
                with st.spinner("Cleaning up..."):
                    if cleanup_auxiliary_files(compiled_files):
                        st.info("🧹 Cleanup successful.")
                    else:
                        st.warning("⚠️ Cleanup failed. Check warnings.")

if not (st.session_state.uploaded_filenames or file_paths_input or github_repo_url):
    st.info("ℹ️ Upload .tex files, enter file paths, or specify a GitHub URL to start compiling.")
