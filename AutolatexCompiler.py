import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional, List
import asyncio
import time
import pyzipper
from github import Github, GithubException

# Page configuration
st.set_page_config(page_title="📝 LaTeX Online Compiler", layout="centered")

# Working directory for compiled PDFs (ephemeral in Streamlit Cloud)
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
        repo_url (str): GitHub repository URL.
        file_path (str): Path to the .tex file in the repository.
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
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex
