import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional, List
import asyncio
import time
import os
import subprocess
import shutil
import pyzipper

# Page configuration
st.set_page_config(page_title="📝 LaTeX Online Compiler", layout="centered")

# Working directory for compiled PDFs
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

# Temporary directory for Git operations
GIT_DIR = Path("git_temp")
GIT_DIR.mkdir(exist_ok=True)

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
                return False, ("❌ Source repository is private. LaTeX.Online requires public repositories. "
                              "Make it public in GitHub: Settings → Danger Zone → Change to public.")
            return True, "✅ Source repository is accessible."
        elif response.status_code == 404:
            return False, "❌ Source repository not found. Check the URL."
        return False, f"❌ Failed to access source repository: Status {response.status_code}"
    except requests.RequestException as e:
        return False, f"❌ Network error checking source repository: {str(e)}"

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

def create_password_protected_zip(pdf_paths: List[Path], zip_password: str) -> Tuple[Optional[Path], str]:
    """
    Create a password-protected ZIP file containing all PDFs.

    Args:
        pdf_paths (List[Path]): List of PDF file paths.
        zip_password (str): Password for the ZIP file.

    Returns:
        Tuple[Optional[Path], str]: Path to ZIP file (or None) and message.
    """
    if not pdf_paths:
        return None, "❌ No PDFs to zip."
    zip_path = WORKING_DIR / f"compiled_pdfs_{int(time.time())}.zip"
    try:
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(zip_password.encode('utf-8'))
            for pdf_path in pdf_paths:
                zf.write(str(pdf_path), pdf_path.name)
        return zip_path, "✅ Password-protected ZIP created successfully."
    except Exception as e:
        return None, f"❌ Failed to create ZIP: {str(e)}"

def push_to_public_repo(repo_url: str, pat: str, folder: str, pdf_paths: List[Path]) -> Tuple[bool, str]:
    """
    Push compiled PDFs to a folder in a public GitHub repository.

    Args:
        repo_url (str): Public GitHub repository URL.
        pat (str): Personal Access Token.
        folder (str): Folder path in the repository (e.g., 'pdfs').
        pdf_paths (List[Path]): List of PDF file paths to push.

    Returns:
        Tuple[bool, str]: (True if successful, message).
    """
    try:
        # Create unique temporary directory for Git operations
        repo_dir = GIT_DIR / f"repo_{int(time.time())}"
        repo_dir.mkdir(exist_ok=True)
        auth_url = repo_url.replace("https://github.com/", f"https://{pat}@github.com/")

        # Clone the repository
        result = subprocess.run(
            ["git", "clone", auth_url, str(repo_dir)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return False, f"❌ Failed to clone repository: {result.stderr[:200]}..."

        # Create folder if it doesn't exist
        target_folder = repo_dir / folder
        target_folder.mkdir(parents=True, exist_ok=True)

        # Copy PDFs to the folder
        for pdf_path in pdf_paths:
            shutil.copy(pdf_path, target_folder / pdf_path.name)

        # Commit and push
        os.chdir(repo_dir)
        subprocess.run(["git", "add", f"{folder}/*.pdf"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add compiled PDFs"], capture_output=True)
        result = subprocess.run(
            ["git", "push", "origin", "master"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            return False, f"❌ Failed to push to repository: {result.stderr[:200]}..."

        # Clean up temporary directory
        shutil.rmtree(repo_dir)
        return True, f"✅ PDFs successfully pushed to {folder} in repository."
    except subprocess.SubprocessError as e:
        return False, f"❌ Git error: {str(e)}"
    except Exception as e:
        return False, f"❌ Error pushing to repository: {str(e)}"
    finally:
        # Reset working directory
        os.chdir(Path.cwd())

def cleanup_pdfs() -> bool:
    """
    Remove all PDF and ZIP files from the working directory.

    Returns:
        bool: True if cleanup successful.
    """
    success = True
    for file in WORKING_DIR.glob("*.pdf"):
        try:
            file.unlink()
        except OSError as e:
            st.warning(f"⚠️ Failed to delete {file.name}: {str(e)}")
            success = False
    for file in WORKING_DIR.glob("*.zip"):
        try:
            file.unlink()
        except OSError as e:
            st.warning(f"⚠️ Failed to delete {file.name}: {str(e)}")
            success = False
    return success

# Streamlit UI
st.title("📝 LaTeX Online Compiler")
st.markdown(
    "Compile multiple LaTeX files from a **public** GitHub repository using LaTeX.Online. "
    "PDFs are saved to a password-protected ZIP file in `compiled_latex`. "
    "Optionally push PDFs to a folder in the public repository."
)

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

# ZIP password
st.subheader("🔒 Password-Protected ZIP")
zip_password = st.text_input(
    "ZIP Password",
    type="password",
    help="Enter a password to protect the ZIP file containing compiled PDFs."
)

# GitHub push options
st.subheader("💾 Push to GitHub Folder (Optional)")
push_to_github = st.checkbox("Push PDFs to GitHub folder", help="Check to push PDFs to a folder in the repository.")
if push_to_github:
    github_folder = st.text_input(
        "GitHub Folder",
        placeholder="e.g., pdfs",
        value="pdfs",
        help="Folder in the repository to store PDFs (e.g., 'pdfs')."
    )
    github_pat = st.text_input(
        "GitHub Personal Access Token",
        type="password",
        help="Enter a PAT with 'repo' scope (GitHub → Settings → Developer settings → Personal access tokens)."
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

                    # Store compiled PDFs in session state
                    if "compiled_pdfs" not in st.session_state:
                        st.session_state.compiled_pdfs = []
                    pdf_paths = []
                    for file_path, pdf_path, logs in results:
                        st.markdown(f"**{file_path}**")
                        if pdf_path and pdf_path.exists():
                            st.success(f"✅ PDF generated: {pdf_path}")
                            st.session_state.compiled_pdfs.append((file_path, pdf_path))
                            pdf_paths.append(pdf_path)
                        else:
                            st.error(f"❌ Compilation failed for {file_path}")
                        if logs:
                            with st.expander(f"🧾 Logs for {file_path}"):
                                st.text(logs)

                    # Create password-protected ZIP
                    if pdf_paths and zip_password:
                        zip_path, zip_message = create_password_protected_zip(pdf_paths, zip_password)
                        st.markdown("**ZIP File**")
                        if zip_path:
                            st.success(zip_message)
                            st.download_button(
                                label=f"Download {zip_path.name}",
                                data=zip_path.read_bytes(),
                                file_name=zip_path.name,
                                mime="application/zip",
                                key=f"download_zip_{zip_path.name}_{str(time.time())}"
                            )
                        else:
                            st.error(zip_message)
                    elif not zip_password:
                        st.error("❌ Please enter a ZIP password.")

                    # Display individual PDF downloads
                    if st.session_state.compiled_pdfs:
                        st.subheader("📥 Download Individual PDFs")
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

                    # Push to GitHub folder
                    if push_to_github and pdf_paths and github_pat and github_folder:
                        st.subheader("💾 Push to GitHub")
                        with st.spinner("Pushing PDFs to GitHub..."):
                            success, push_message = push_to_public_repo(github_repo_url, github_pat, github_folder, pdf_paths)
                            if success:
                                st.success(push_message)
                            else:
                                st.error(push_message)

                    # Cleanup button
                    if st.session_state.compiled_pdfs and st.button("🧹 Clear Compiled Files"):
                        with st.spinner("Cleaning up..."):
                            if cleanup_pdfs():
                                st.info("🧹 All PDFs and ZIPs cleared from compiled_latex.")
                                st.session_state.compiled_pdfs = []
                            else:
                                st.warning("⚠️ Cleanup failed. Check warnings.")

if not (github_repo_url and github_file_paths):
    st.info("ℹ️ Enter a GitHub URL and .tex file paths to start compiling.")
