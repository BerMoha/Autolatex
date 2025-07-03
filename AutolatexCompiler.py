import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional, List
import asyncio
import time
import os
import pyzipper
from github import Github, GithubException

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

def push_to_github_repo(repo_url: str, pat: str, folder: str, pdf_paths: List[Path]) -> Tuple[bool, str]:
    """
    Push compiled PDFs to a folder in a GitHub repository using PyGitHub.

    Args:
        repo_url (str): GitHub repository URL.
        pat (str): Personal Access Token.
        folder (str): Folder path in the repository (e.g., 'pdfs').
        pdf_paths (List[Path]): List of PDF file paths to push.

    Returns:
        Tuple[bool, str]: (True if successful, message).
    """
    try:
        # Initialize GitHub client
        g = Github(pat)
        repo_name = repo_url.split("github.com/")[1].rstrip('.git')
        repo = g.get_repo(repo_name)

        # Check if folder exists; create if not
        try:
            repo.get_contents(folder)
        except GithubException:
            repo.create_file(f"{folder}/.gitkeep", "Create folder", "", branch="master")

        # Upload each PDF
        for pdf_path in pdf_paths:
            with open(pdf_path, 'rb') as f:
