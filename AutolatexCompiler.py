
import streamlit as st
import urllib.parse
import requests

st.title("Compile LaTeX from any Public GitHub Repository")

repo_owner = st.text_input("GitHub owner or organization (e.g. BerMoha):")
repo_name = st.text_input("Repository name (e.g. Autolatex):")
file_path = st.text_input("Path to .tex file in repository (e.g. main.tex or docs/paper.tex):")
branch = st.text_input("Branch (default: main)", value="main")

if repo_owner and repo_name and file_path:
    git_url = f"https://github.com/{repo_owner}/{repo_name}"
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = (
        f"https://latexonline.cc/compile?"
        f"git={git_url}&target={encoded_file_path}&command=pdflatex&branch={urllib.parse.quote(branch)}"
    )
    st.write(f"API request: {api_url}")

    response = requests.get(api_url)
    if response.status_code == 200 and response.headers.get("Content-Type", "").startswith("application/pdf"):
        st.success("Compilation succeeded! Download your PDF below.")
        st.download_button(
            "Download PDF",
            response.content,
            file_name=file_path.replace(".tex", ".pdf"),
            mime="application/pdf"
        )
    else:
        st.error("Compilation failed! Please check your repository info and .tex file path.")
        if response.content:
            st.text_area("API response", response.text, height=200)
