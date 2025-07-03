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

# Working directory for temporary files
WORKING_DIR = Path("compiled_latex")
WORKING_DIR.mkdir(exist_ok=True)

async def compile_latex_from_github(repo_url: str, file_path: str, output_dir: Optional[Path]) -> Tuple[Optional[Path], str]:
    """
    Compile a LaTeX file from a GitHub repository using LaTeX.Online.

    Args:
        repo_url (str): GitHub repository URL (e.g., https://github.com/username/repo).
        file_path (str): Path to the .tex file in the repository (e.g., main.tex).
        output_dir (Optional[Path]): Directory to save the PDF.

    Returns:
        Tuple[Optional[Path], str]: Path to PDF (or None) and compilation logs.
    """
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, f"❌ File {file_path} must be a .tex file."

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
        return None, f"❌ Compilation error for {file_path}: Status {response.status_code}\n{response.text[:100]}..."
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {file_path}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {file_path}: {str(e)}"

async def compile_multiple_files(repo_url: str, file_paths: List[str], output_dir: Optional[Path]) -> List[Tuple[str, Optional[Path], str]]:
    """
    Compile multiple LaTeX files concurrently from a GitHub repository.

    Args:
        repo_url (str): GitHub repository URL.
        file_paths (List[str]): List of .tex file paths.
        output_dir (Optional[Path]): Directory to save PDFs.

    Returns:
        List[Tuple[str, Optional[Path], str]]: List of (file_path, PDF path, logs) for each file.
    """
    tasks = [compile_latex_from_github(repo_url, file_path, output_dir) for file_path in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [(file_paths[i], *results[i]) for i in range(len(file_paths))]

# Streamlit UI
st.title("📝 LaTeX Online Compiler")
st.markdown("Compile multiple LaTeX files from a GitHub repository using LaTeX.Online. Enter file paths separated by commas.")

# Configuration
st.subheader("⚙️ Settings")
output_dir_input = st.text_input(
    "Output Directory (optional)",
    placeholder="e.g., C:/Users/pc/Desktop/Autolatex",
    help="Local folder to save PDFs (e.g., C:/Users/pc/Desktop/Autolatex). Leave blank to use working directory."
)
output_dir = None
if output_dir_input:
    # Normalize input
    output_dir_input = output_dir_input.strip().replace('/', '\\')
    # Check if input is a URL
    if output_dir_input.lower().startswith(('http://', 'https://')):
        st.error(f"❌ Output directory cannot be a URL: {output_dir_input}. Use a local path like C:/Users/pc/Desktop/Autolatex.")
    else:
        try:
            output_dir = Path(output_dir_input)
            st.info(f"Checking directory: {output_dir}")
            # Check with os.path for additional debugging
            if os.path.exists(str(output_dir)):
                st.info(f"os.path.exists confirms directory exists: {output_dir}")
            else:
                st.warning(f"os.path.exists reports directory missing: {output_dir}")
            # Create directory if it doesn't exist
            if not output_dir.exists():
                st.info(f"Directory {output_dir} does not exist. Attempting to create it...")
                output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                st.error(f"❌ Path is not a directory: {output_dir_input}")
                output_dir = None
            else:
                st.info(f"Using output directory: {output_dir}")
        except PermissionError as e:
            st.error(f"❌ Permission denied for directory {output_dir_input}: {str(e)}")
            output_dir = None
        except Exception as e:
            st.error(f"❌ Error accessing directory {output_dir_input}: {str(e)}")
            output_dir = None

# GitHub input
st.subheader("📦 Compile from GitHub")
github_repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="e.g., https://github.com/BerMoha/Autolatex",
    value="https://github.com/BerMoha/Autolatex"
)
github_file_paths = st.text_input(
    "Main .tex File Paths (comma-separated)",
    placeholder="e.g., main.tex,chapter1.tex,chapter2.tex"
)

# Compile button
if github_repo_url and github_file_paths:
    if st.button("📄 Compile Files"):
        file_paths = [fp.strip() for fp in github_file_paths.split(',') if fp.strip()]
        if not file_paths:
            st.error("❌ No valid file paths provided.")
        else:
            with st.spinner(f"Compiling {len(file_paths)} file(s) from GitHub..."):
                # Run async compilation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(compile_multiple_files(github_repo_url, file_paths, output_dir))
                loop.close()

                # Display results
                for file_path, pdf_path, logs in results:
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
                    else:
                        st.error(f"❌ Compilation failed for {file_path}")
                    if logs:
                        with st.expander(f"🧾 Logs for {file_path}"):
                            st.text(logs)

if not (github_repo_url and github_file_paths):
    st.info("ℹ️ Enter a GitHub URL and .tex file paths to start compiling.")
