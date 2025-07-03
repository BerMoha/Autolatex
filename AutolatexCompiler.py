import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional, List
import asyncio
import time
import pyzipper
from github import Github, GithubException

# Configuration
st.set_page_config(page_title="📝 LaTeX Online Compiler", layout="centered")
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

# Utility Functions
def check_repository_access(repo_url: str) -> Tuple[bool, str]:
    if not repo_url.startswith("https://github.com/"):
        return False, "❌ Invalid GitHub URL. Must start with https://github.com/"
    try:
        repo_path = repo_url.split('github.com/')[1].rstrip('/')
        response = requests.get(f"https://api.github.com/repos/{repo_path}", timeout=10)
        if response.status_code == 200:
            if response.json().get("private", True):
                return False, "❌ Repository is private. Make it public to compile."
            return True, "✅ Repository is accessible."
        elif response.status_code == 404:
            return False, "❌ Repository not found."
        return False, f"❌ Failed to access repository: Status {response.status_code}"
    except requests.RequestException as e:
        return False, f"❌ Network error: {str(e)}"

async def compile_latex_from_github(repo_url: str, file_path: str, index: int) -> Tuple[Optional[Path], str]:
    if not repo_url.startswith("https://github.com/") or not file_path.lower().endswith('.tex'):
        return None, "❌ Invalid inputs."

    base_name = Path(file_path).stem.replace(' ', '_')
    temp_pdf = WORKING_DIR / f"{base_name}_{index}_{int(time.time())}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_path}&command=pdflatex"

    try:
        resp = requests.get(api_url, headers={'Accept': 'application/pdf'}, timeout=60)
        if resp.status_code == 200 and 'application/pdf' in resp.headers.get('Content-Type', ''):
            with open(temp_pdf, 'wb') as f:
                f.write(resp.content)
            return temp_pdf, "✅ Compilation successful."
        return None, f"❌ Compilation failed: Status {resp.status_code}"
    except requests.Timeout:
        return None, "❌ Compilation timed out."
    except requests.RequestException as e:
        return None, f"❌ Network error: {str(e)}"

async def compile_multiple_files(repo_url: str, file_paths: List[str]) -> List[Tuple[str, Optional[Path], str]]:
    tasks = [compile_latex_from_github(repo_url, path, i) for i, path in enumerate(file_paths)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            output.append((file_paths[i], None, f"❌ Error: {str(result)}"))
        else:
            output.append((file_paths[i], *result))
    return output

def create_password_protected_zip(pdf_paths: List[Path], password: str) -> Tuple[Optional[Path], str]:
    if not pdf_paths:
        return None, "❌ No PDFs to zip."
    zip_path = WORKING_DIR / f"compiled_pdfs_{int(time.time())}.zip"
    try:
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            for pdf in pdf_paths:
                zf.write(str(pdf), pdf.name)
        return zip_path, "✅ ZIP created."
    except Exception as e:
        return None, f"❌ ZIP creation error: {str(e)}"

def push_to_github_repo(repo_url: str, pat: str, folder: str, pdfs: List[Path]) -> Tuple[bool, str]:
    try:
        g = Github(pat)
        repo_name = repo_url.split("github.com/")[1].rstrip('.git')
        repo = g.get_repo(repo_name)
        branch = repo.default_branch

        try:
            repo.get_contents(folder)
        except GithubException:
            repo.create_file(f"{folder}/.gitkeep", "Init folder", "", branch=branch)

        for pdf in pdfs:
            with open(pdf, 'rb') as f:
                content = f.read()
            file_path = f"{folder}/{pdf.name}"
            try:
                existing = repo.get_contents(file_path, ref=branch)
                repo.update_file(file_path, f"Update {pdf.name}", content, existing.sha, branch=branch)
            except GithubException:
                repo.create_file(file_path, f"Add {pdf.name}", content, branch=branch)

        return True, "✅ PDFs pushed to GitHub."
    except Exception as e:
        return False, f"❌ Push failed: {str(e)}"

def cleanup_files():
    for file in WORKING_DIR.glob("*.*"):
        try:
            file.unlink()
        except Exception as e:
            st.warning(f"⚠️ Could not delete {file.name}: {e}")

# UI
st.title("📝 LaTeX Online Compiler")

st.markdown("Compile LaTeX files from a public GitHub repository using LaTeX.Online. Requires internet connection.")

if not st.connection("internet", type="http"):
    st.error("❌ This app requires an internet connection to work.")
    st.stop()

repo_url = st.text_input("GitHub Repository", value="https://github.com/BerMoha/Autolatex")
file_paths = st.text_input(".tex File Paths (comma-separated)", value="Fourier VS Dunkl.tex")
password = st.text_input("ZIP Password", type="password")
push = st.checkbox("Push to GitHub")
folder = st.text_input("Target Folder in Repo", value="pdfs") if push else None
pat = st.text_input("GitHub PAT", type="password") if push else None

if repo_url:
    accessible, message = check_repository_access(repo_url)
    st.info(message) if accessible else st.error(message)

if st.button("📄 Compile") and accessible:
    tex_files = [fp.strip() for fp in file_paths.split(',') if fp.strip().endswith('.tex')]
    if not tex_files:
        st.error("❌ No valid .tex files provided.")
    else:
        st.session_state.compiled_pdfs = []
        with st.spinner("Compiling..."):
            try:
                results = asyncio.run(compile_multiple_files(repo_url, tex_files))
            except RuntimeError:
                results = asyncio.get_event_loop().run_until_complete(compile_multiple_files(repo_url, tex_files))

            for file, pdf, log in results:
                st.markdown(f"**{file}**")
                if pdf:
                    st.success("✅ Compiled successfully.")
                    st.download_button(f"Download {pdf.name}", pdf.read_bytes(), pdf.name, mime="application/pdf")
                    st.session_state.compiled_pdfs.append(pdf)
                else:
                    st.error(log)

        if password and st.session_state.compiled_pdfs:
            zip_path, msg = create_password_protected_zip(st.session_state.compiled_pdfs, password)
            if zip_path:
                st.success(msg)
                st.download_button("Download ZIP", zip_path.read_bytes(), zip_path.name, mime="application/zip")
            else:
                st.error(msg)

        if push and pat and st.session_state.compiled_pdfs:
            with st.spinner("Pushing to GitHub..."):
                success, msg = push_to_github_repo(repo_url, pat, folder, st.session_state.compiled_pdfs)
                st.success(msg) if success else st.error(msg)

        if st.button("🧹 Clean Up"):
            cleanup_files()
            st.session_state.compiled_pdfs = []
            st.info("🧹 Files cleaned.")
