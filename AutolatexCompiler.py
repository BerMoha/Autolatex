
import streamlit as st
import urllib.parse
import requests

st.title("Compile LaTeX from GitHub")

git_url = st.text_input("GitHub repository URL (e.g. https://github.com/owner/repo):")
file_path = st.text_input("Path to .tex file in repository (e.g. main.tex or docs/paper.tex):")

if git_url and file_path:
    encoded_file_path = urllib.parse.quote(file_path)
    api_url = f"https://latexonline.cc/compile?git={git_url}&target={encoded_file_path}&command=pdflatex"
    st.write(f"API request: {api_url}")

    # Download the PDF from the API
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
        st.error("Compilation failed! Please check your repository URL and .tex file path.")
        if response.content:
            st.text_area("API response", response.text, height=200)
        st.error(f"Error: {str(e)}")
