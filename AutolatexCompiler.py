import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional, List
import asyncio
import time
import os

# Page configuration
st.set_page_config(page_title="📝 LaTeX Online Compiler", layout="centered")

# Working directory for compiled PDFs
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

def check_repository_access(repo_url: str) -> Tuple[bool, str]:
    """
    Check if the GitHub repository is accessible.

    Args:
        repo_url (str): GitHub repository URL.

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
                return False, ("❌ Repository is private. LaTeX.Online requires public repositories. "
                              "Make it public in GitHub: Settings → Danger Zone → Change to public.")
            return True, "✅ Repository is accessible."
        elif response.status_code == 404:
            return False, "❌ Repository not found. Check the URL."
        return False, f"❌ Failed to access repository: Status {response.status_code}"
    except requests.RequestException as e:
        return False, f"❌ Network error checking repository: {str(e)}"

async def compile_latex_from_github(repo_url: str, file_path: str, index: int) -> Tuple[Optional[Path], str]:
    """
    Compile a LaTeX file from a GitHub repository using LaTeX.Online.

    Args:
        repo_url (str): GitHub repository URL (e.g., https://github.com/username/repo).
        file_path (str): Path to the .tex file in the repository (e.g., main.tex).
        index (int): Index to ensure unique PDF names.

    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and compilation logs.
    """
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, f"❌ File {file_path} must be a .tex file."

    # Generate unique PDF name with index to avoid overwriting
    base_name = Path(file_path).stem.replace(' ', '_')
    temp_pdf = WORKING_DIR / f"{base_name}_{index}_{int(time.time())}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    try:
        response = requests.get(api_url, headers={'Accept': 'application/pdf'}, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(response.content)
            return temp_pdf, "✅ Compilation successful"
        return None, f"❌ Compilation error for {file_path}: Status {response.status_code}\n{response.text[:200]}..."
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {file_path}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {file_path}: {str(e)}"

async def compile_multiple_files(repo_url: str, file_paths: List[str]) -> List[Tuple[str, Optional[Path], str]]:
    """
    Compile multiple LaTeX files concurrently from a GitHub repository.

    Args:
        repo_url (str): GitHub repository URL.
        file_paths (List[str]): List of .tex file paths.

    Returns:
        List[Tuple[str, Optional[Path], str]]: List of (file_path, PDF path, logs) for each file.
    """
    tasks = [compile_latex_from_github(repo_url, file_path, i) for i, file_path in enumerate(file_paths)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [(file_paths[i], *results[i]) for i in range(len(file_paths))]

def cleanup_pdfs() -> bool:
    """
    Remove all PDF files from the working directory.

    Returns:
        bool: True if cleanup successful.
    """
    success = True
    for pdf_file in WORKING_DIR.glob("*.pdf"):
        try:
            pdf_file.unlink()
        except OSError as e:
            st.warning(f"⚠️ Failed to delete {pdf_file.name}: {str(e)}")
            success = False
    return success

# Streamlit UI
st.title("📝 LaTeX Online Compiler")
st.markdown("Compile multiple LaTeX files from a **public** GitHub repository using LaTeX.Online. "
            "Enter file paths separated by commas. PDFs are saved to compiled_latex directory.")

# GitHub input
st.subheader("📦 Compile from GitHub")
github_repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="e.g., https://github.com/BerMoha/Autolatex",
    value="https://github.com/BerMoha/Autolatex"
)
github_file_paths = st.text_input(
    "Main .tex File Paths (comma-separated)",
    placeholder="e.g., main.tex,chapter1.tex",
    value="Fourier VS Dunkl.tex",
    help="Enter file paths (e.g., 'Fourier VS Dunkl.tex' or 'src/Fourier VS Dunkl.tex'). Spaces are supported."
)

# Validate repository
if github_repo_url:
    is_accessible, repo_message = check_repository_access(github_repo_url)
    if is_accessible:
        st.success(repo_message)
    else:
        st.error(repo_message)

# Compile button
if github_repo_url and github_file_paths:
    if st.button("📄 Compile Files"):
        file_paths = [fp.strip() for fp in github_file_paths.split(',') if fp.strip()]
        if not file_paths:
            st.error("❌ No valid file paths provided.")
        else:
            if not is_accessible:
                st.error(f"❌ Cannot compile: {repo_message}")
            else:
                with st.spinner(f"Compiling {len(file_paths)} file(s) from GitHub..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(compile_multiple_files(github_repo_url, file_paths))
                    loop.close()

                    # Store compiled PDFs in session state for persistence
                    if "compiled_pdfs" not in st.session_state:
                        st.session_state.compiled_pdfs = []
                    for file_path, pdf_path, logs in results:
                        st.markdown(f"**{file_path}**")
                        if pdf_path and pdf_path.exists():
                            st.success(f"✅ PDF generated: {pdf_path}")
                            st.session_state.compiled_pdfs.append((file_path, pdf_path))
                        else:
                            st.error(f"❌ Compilation failed for {file_path}")
                        if logs:
                            with st.expander(f"🧾 Logs for {file_path}"):
                                st.text(logs)

                    # Display download buttons for all compiled PDFs
                    if st.session_state.compiled_pdfs:
                        st.subheader("📥 Download Compiled PDFs")
                        for file_path, pdf_path in st.session_state.compiled_pdfs:
                            if pdf_path.exists():
                                st.download_button(
                                    label=f"Download {pdf_path.name} ({file_path})",
                                    data=pdf_path.read_bytes(),
                                    file_name=pdf_path.name,
                                    mime="application/pdf",
                                    key=f"download_{file_path}_{pdf_path.name}_{str(time.time())}"
                                )
                            else:
                                st.warning(f"⚠️ PDF not found: {pdf_path}")

                    # Cleanup button
                    if st.session_state.compiled_pdfs and st.button("🧹 Clear Compiled PDFs"):
                        with st.spinner("Cleaning up..."):
                            if cleanup_pdfs():
                                st.info("🧹 All PDFs cleared from compiled_latex.")
                                st.session_state.compiled_pdfs = []
                            else:
                                st.warning("⚠️ Cleanup failed. Check warnings.")

if not (github_repo_url and github_file_paths):
    st.info("ℹ️ Enter a GitHub URL and .tex file paths to start compiling.")
