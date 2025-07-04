import streamlit as st
import requests
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional
import shutil

# Suppress Streamlit warnings
import warnings
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")

# Page config
st.set_page_config(page_title="📝 LaTeX Online Compiler", layout="centered")

# Working directory for PDFs
WORKING_DIR = Path("compiled_latex")

# Optional: Clean up WORKING_DIR at startup
def cleanup_working_dir():
    """
    Delete the compiled_latex folder if it exists.
    """
    if WORKING_DIR.exists():
        try:
            shutil.rmtree(WORKING_DIR)
            st.info("🧹 Cleared existing compiled_latex directory.")
        except OSError as e:
            st.warning(f"⚠️ Failed to clear compiled_latex directory: {str(e)}")
    WORKING_DIR.mkdir(exist_ok=True)

# Run cleanup at startup (comment out if not desired)
cleanup_working_dir()

def compile_latex_from_github(repo_url: str, file_path: str) -> Tuple[Optional[Path], str]:
    """
    Compile LaTeX file from a GitHub repository using LaTeX.Online's Git endpoint.
    
    Args:
        repo_url (str): GitHub repository URL (e.g., https://github.com/username/repo).
        file_path (str): Path to the main .tex file in the repository.
    
    Returns:
        Tuple[Optional[Path], str]: Path to generated PDF (or None) and compilation logs.
    """
    if not repo_url.startswith("https://github.com/"):
        return None, "❌ Invalid GitHub repository URL. Must start with https://github.com/"
    if not file_path.lower().endswith('.tex'):
        return None, "❌ File path must point to a .tex file"

    pdf_path = WORKING_DIR / f"{Path(file_path).stem}.pdf"
    git_url = repo_url.rstrip('/') + '.git'
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"

    headers = {'Accept': 'application/pdf'}
    try:
        with st.spinner(f"Fetching and compiling {file_path} from GitHub..."):
            response = requests.get(api_url, headers=headers, timeout=60)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            with open(pdf_path, 'wb') as f:
                f.write(response.content)
            return pdf_path, "✅ Compilation successful"
        else:
            return None, f"❌ Compilation error for {file_path}:\nStatus: {response.status_code}\n{response.text}"
    except requests.Timeout:
        return None, f"❌ Compilation timed out for {file_path}"
    except requests.RequestException as e:
        return None, f"❌ Network error for {file_path}: {str(e)}"

# Streamlit UI
st.title("📝 LaTeX Online Compiler")
st.markdown("""
Compile LaTeX files into PDFs directly from a GitHub repository using LaTeX.Online.
Enter the repository URL and the path to your main `.tex` file and download your file. 
""")

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
    if st.button("Compile from GitHub", key="compile_github"):
        with st.spinner(f"Compiling {github_file_path} from GitHub..."):
            pdf_path, logs = compile_latex_from_github(github_repo_url, github_file_path)
            
            st.markdown(f"**{github_file_path}**")
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
                    st.text(logs)  # This should be indented with 16 spaces
else:
    st.info("ℹ️ Enter a GitHub repository URL and file path to start compiling.")
